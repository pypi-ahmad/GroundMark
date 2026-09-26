"""Standalone PP-DocLayoutV3 runtime; no parser, UI, or Sol dependencies.

Optional inference packages are imported on first preparation or prediction. The default
accessor shares one locked model per process, not document results.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from threading import RLock
from time import perf_counter
from typing import Literal, Protocol

from PIL import Image

from src.config import LayoutConfig, layout_config

MODEL_ID = "PaddlePaddle/PP-DocLayoutV3_safetensors"
REVISION = "97d101e6db2642e162a1d05392d1b0231c91033e"
# Hashes of the official pinned snapshot, also enforced for offline overrides.
MODEL_FILES = {
    "config.json": "3cf834b91d23a756b1519bce4db42c09e852f3e35c35092dd5a3e253a50c071a",
    "preprocessor_config.json": "519fe0187a43a1ca429e3ad8317bab8700f0d5e8fb3a6e3a0a413ffac078ba42",
    "model.safetensors": "5ea422c6cc5fe759a47e1357c35639b58173508e025a3131cbe4b6ac59e2b85e",
    "inference.yml": "506fcfac13b3b546ae40d7886b44126420f392adb694e3f8bb6a6286a1f90fdc",
}
LABELS = tuple((
    "abstract algorithm aside_text chart content display_formula doc_title "
    "figure_title footer footer_image footnote formula_number header header_image "
    "image inline_formula number paragraph_title reference reference_content seal "
    "table text vertical_text vision_footnote"
).split())
DETECTION_THRESHOLD = 0.5  # Upstream detection/mask threshold, not matching IoU.
Device = Literal["cpu", "cuda"]


@dataclass(frozen=True)
class LayoutReadiness:
    """Actual verified device, CPU fallback reason, preparation time, and reuse."""
    device: Device
    fallback_reason: Literal["cuda_unavailable", "cuda_probe_failed"] | None
    preparation_seconds: float
    reused: bool


class LayoutModelUnavailable(RuntimeError):
    """Safe, actionable initialization failure; no provider/native error text."""
    def __init__(self, code: str, *, attempted_devices: tuple[str, ...] = ()):
        self.code = code
        self.attempted_devices = attempted_devices
        actions = {
            "dependencies_unavailable": "Install the layout extra with uv sync --extra layout; check native library availability.",
            "download_failed": "Check Hub connectivity or set GROUNDMARK_LAYOUT_MODEL_DIR to the pinned official snapshot.",
            "invalid_model": "Use all four unmodified files from the pinned official V3 snapshot.",
            "model_load_failed": "Check the layout extra and pinned model files.",
            "devices_failed": "The model could not run on the attempted devices. Check native dependencies and available memory.",
        }
        super().__init__(f"PP-DocLayoutV3 unavailable ({code}). {actions[code]}")


class LayoutInferenceError(RuntimeError):
    """A page failed after initialization; no automatic per-page device retry."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"PP-DocLayoutV3 page prediction failed ({code}).")


@dataclass(frozen=True)
class LayoutRegion:
    """One V3 detection with pixel box/polygon geometry and native order rank."""
    class_id: int
    label: str
    score: float
    box_px: tuple[float, float, float, float]
    polygon_px: tuple[tuple[float, float], ...]
    order: int | None


@dataclass(frozen=True)
class LayoutPageResult:
    """One page's immutable pixel regions and runtime/model provenance."""
    page: int
    width_px: int
    height_px: int
    regions: tuple[LayoutRegion, ...]
    device: Device
    fallback_reason: Literal["cuda_unavailable", "cuda_probe_failed"] | None
    model_id: str = MODEL_ID
    revision: str = REVISION
    engine: str = "transformers"
    order_base: int = 0


class LayoutBackend(Protocol):
    """Inject this small backend contract instead of importing ML libraries."""
    @property
    def device(self) -> Device: ...
    def cuda_available(self) -> bool: ...
    def use_device(self, device: Device) -> None: ...
    def predict(self, image: Image.Image) -> tuple[LayoutRegion, ...]: ...


def _verify_files(directory: Path) -> None:
    try:
        for filename, expected in MODEL_FILES.items():
            with (directory / filename).open("rb") as handle:
                actual = hashlib.file_digest(handle, "sha256").hexdigest()
            if actual != expected:
                raise ValueError("Snapshot checksum mismatch")
    except (OSError, ValueError) as exc:
        raise LayoutModelUnavailable("invalid_model") from exc


def resolve_model_snapshot(config: LayoutConfig, *, downloader: Callable | None = None) -> Path:
    """Reuse a complete pinned user-cache snapshot; download only on a miss."""
    if config.model_dir is not None:
        _verify_files(config.model_dir)
        return config.model_dir
    if downloader is None:
        try:
            from huggingface_hub import snapshot_download
        except (ImportError, OSError) as exc:
            raise LayoutModelUnavailable("dependencies_unavailable") from exc
        downloader = snapshot_download
    options = dict(repo_id=MODEL_ID, revision=REVISION, allow_patterns=list(MODEL_FILES))
    try:
        directory = Path(downloader(**options, local_files_only=True))
        complete = all((directory / name).is_file() for name in MODEL_FILES)
    except Exception:
        complete = False
    if not complete:
        try:
            directory = Path(downloader(**options, local_files_only=False))
        except Exception as exc:
            raise LayoutModelUnavailable("download_failed") from exc
    _verify_files(directory)
    return directory


def _regions(output: dict, width: int, height: int) -> tuple[LayoutRegion, ...]:
    """Adapt the official postprocessor output, without decoding model heads."""
    try:
        scores, labels, boxes, orders = [
            output[key].detach().cpu().tolist() for key in ("scores", "labels", "boxes", "order_seq")
        ]
        polygons = output["polygon_points"]
        if len({len(v) for v in (scores, labels, boxes, orders, polygons)}) != 1:
            raise ValueError("Inconsistent output lengths")
        if orders != sorted(orders) or any(type(rank) is not int or not 0 <= rank < 300 for rank in orders):
            raise ValueError("Invalid reading-order ranks")
        regions = []
        for score, label, box, polygon, order in zip(scores, labels, boxes, polygons, orders):
            if type(label) is not int or not 0 <= label < len(LABELS):
                raise ValueError("Unknown class")
            points = polygon.tolist()
            if not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError("Invalid score")
            if len(box) != 4 or not all(math.isfinite(v) for v in box):
                raise ValueError("Invalid box")
            x0, y0, x1, y1 = box
            if not (max(0, x0) < min(width, x1) and max(0, y0) < min(height, y1)):
                raise ValueError("Box does not intersect the page")
            if len(points) < 3 or any(len(point) != 2 or not all(math.isfinite(v) for v in point) for point in points):
                raise ValueError("Invalid polygon")
            regions.append(LayoutRegion(label, LABELS[label], float(score), tuple(box),
                                        tuple(tuple(point) for point in points), order))
        return tuple(regions)
    except Exception as exc:
        raise LayoutInferenceError("invalid_output") from exc


class _TransformersBackend:
    def __init__(self, directory: Path):
        try:
            import torch
            import cv2
            import torchvision
            from transformers import AutoImageProcessor, AutoModelForObjectDetection
        except (ImportError, OSError) as exc:
            raise LayoutModelUnavailable("dependencies_unavailable") from exc
        self.torch = torch
        self.processor = AutoImageProcessor.from_pretrained(directory, local_files_only=True, trust_remote_code=False)
        self.model = AutoModelForObjectDetection.from_pretrained(
            directory, local_files_only=True, trust_remote_code=False,
            use_safetensors=True, dtype=torch.float32,
        ).eval()

    @property
    def device(self) -> Device:
        devices = {parameter.device.type for parameter in self.model.parameters()}
        if len(devices) != 1 or not devices <= {"cpu", "cuda"}:
            raise RuntimeError("Model has an unsupported or mixed device placement")
        return next(iter(devices))

    def cuda_available(self) -> bool:
        return self.torch.cuda.is_available()

    def use_device(self, device: Device) -> None:
        self.model.to(device)

    def predict(self, image: Image.Image) -> tuple[LayoutRegion, ...]:
        device = self.device
        inputs = self.processor(images=image, return_tensors="pt").to(device)
        if any(tensor.device.type != device for tensor in inputs.values()):
            raise RuntimeError("Processor tensors are on the wrong device")
        with self.torch.inference_mode():
            outputs = self.model(**inputs)
        if any(getattr(outputs, name).device.type != device
               for name in ("logits", "pred_boxes", "order_logits", "out_masks")):
            raise RuntimeError("Model output tensors are on the wrong device")
        if device == "cuda":
            self.torch.cuda.synchronize()
        output = self.processor.post_process_object_detection(
            outputs, threshold=DETECTION_THRESHOLD, target_sizes=[(image.height, image.width)],
        )[0]
        return _regions(output, image.width, image.height)


class LayoutRuntime:
    """Lazy, serialized predictor with injected model resolution and backend."""
    def __init__(self, config: LayoutConfig | None = None, *,
                 snapshot_resolver: Callable[[LayoutConfig], Path] = resolve_model_snapshot,
                 backend_factory: Callable[[Path], LayoutBackend] = _TransformersBackend):
        self.config = config if config is not None else layout_config()
        self._resolve = snapshot_resolver
        self._factory = backend_factory
        self._backend: LayoutBackend | None = None
        self._fallback_reason = None
        self._lock = RLock()

    def _initialize(self) -> LayoutBackend:
        # Called only under the prediction lock. Publish the backend after its
        # complete processor/model/postprocessor probe succeeds, never before.
        self._fallback_reason = None
        directory = self._resolve(self.config)
        try:
            backend = self._factory(directory)
        except LayoutModelUnavailable:
            raise
        except (ImportError, OSError) as exc:
            raise LayoutModelUnavailable("dependencies_unavailable") from exc
        except Exception as exc:
            raise LayoutModelUnavailable("model_load_failed") from exc
        attempted = []
        probe = Image.new("RGB", (96, 128), "white")
        if self.config.device == "auto":
            try:
                if backend.cuda_available():
                    attempted.append("cuda")
                    backend.use_device("cuda")
                    if backend.device != "cuda":
                        raise RuntimeError("CUDA placement was not honored")
                    backend.predict(probe)
                    if backend.device != "cuda":
                        raise RuntimeError("CUDA probe changed device")
                    self._backend = backend
                    return backend
                self._fallback_reason = "cuda_unavailable"
            except Exception:
                self._fallback_reason = "cuda_probe_failed"
        attempted.append("cpu")
        try:
            backend.use_device("cpu")
            if backend.device != "cpu":
                raise RuntimeError("CPU placement was not honored")
            backend.predict(probe)
            if backend.device != "cpu":
                raise RuntimeError("CPU probe changed device")
        except Exception as exc:
            raise LayoutModelUnavailable("devices_failed", attempted_devices=tuple(attempted)) from exc
        self._backend = backend
        return backend

    def prepare(self) -> LayoutReadiness:
        """Verify initialization/device once, before any paid page requests."""
        started = perf_counter()
        with self._lock:
            reused = self._backend is not None
            if self._backend is None:
                self._initialize()
            return LayoutReadiness(self._backend.device, self._fallback_reason,
                                   perf_counter() - started, reused)

    def predict(self, image: Image.Image, page_number: int = 1) -> LayoutPageResult:
        """Analyze one PIL image; return pixel regions and the actual device.

        Preparation is lazy and shared by later calls. Invalid image/page inputs
        raise ValueError; initialization raises LayoutModelUnavailable and a
        failed page prediction raises LayoutInferenceError. This runtime never
        calls Sol; the document parser owns transcription fallback.
        """
        if not isinstance(image, Image.Image) or image.width <= 0 or image.height <= 0:
            raise ValueError("Layout prediction requires one nonempty PIL image")
        if type(page_number) is not int or page_number < 1:
            raise ValueError("page_number must be a positive integer")
        with self._lock:
            backend = self._backend if self._backend is not None else self._initialize()
            try:
                regions = backend.predict(image.convert("RGB"))
                device = backend.device
            except LayoutInferenceError:
                raise
            except Exception as exc:
                raise LayoutInferenceError("inference_failed") from exc
            return LayoutPageResult(page_number, image.width, image.height, regions,
                                    device, self._fallback_reason)


_singleton: LayoutRuntime | None = None
_singleton_lock = RLock()


def get_layout_runtime() -> LayoutRuntime:
    """One runtime per process; restart the process to change configuration."""
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = LayoutRuntime()
        return _singleton
