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

MODEL_ID = "PaddlePaddle/PP-DocLayoutV3_onnx"
REVISION = "46bbdf188bb0a772c08aed74882ce7e51a8f1ea6"
# Hashes of the official pinned snapshot, also enforced for offline overrides.
MODEL_FILES = {
    "inference.onnx": "45bf71750b00739a41fc209f132eb104a4d6b5bb29483c9078164d8b87cf28ba",
    "inference.yml": "506fcfac13b3b546ae40d7886b44126420f392adb694e3f8bb6a6286a1f90fdc",
}
LABELS = tuple((
    "abstract algorithm aside_text chart content display_formula doc_title "
    "figure_title footer footer_image footnote formula_number header header_image "
    "image inline_formula number paragraph_title reference reference_content seal "
    "table text vertical_text vision_footnote"
).split())
DETECTION_THRESHOLD = 0.5  # Selection only; the exported mask threshold is fixed at 0.5.
Device = Literal["cpu", "cuda"]
FallbackReason = Literal["cuda_unavailable", "cuda_probe_failed", "cuda_execution_failed"]


@dataclass(frozen=True)
class LayoutReadiness:
    """Actual verified device, CPU fallback reason, preparation time, and reuse."""
    device: Device
    fallback_reason: FallbackReason | None
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
            "invalid_model": "Use inference.onnx and inference.yml from the pinned ONNX snapshot; safetensors folders are incompatible.",
            "model_load_failed": "Check the layout extra and pinned model files.",
            "devices_failed": "The model could not run on the attempted devices. Check native dependencies and available memory.",
        }
        super().__init__(f"PP-DocLayoutV3 unavailable ({code}). {actions[code]}")


class LayoutInferenceError(RuntimeError):
    """Safe page failure; only native execution errors qualify for recovery."""
    def __init__(self, code: str, *, device: Device | None = None, failures: tuple[str, ...] = (),
                 fallback_reason: FallbackReason | None = None):
        self.code, self.device, self.failures = code, device, failures
        self.fallback_reason = fallback_reason
        super().__init__(f"PP-DocLayoutV3 page prediction failed ({code}).")


class LayoutExecutionError(LayoutInferenceError):
    """Raised only around native execution, never preprocessing or decoding."""


@dataclass(frozen=True)
class LayoutRegion:
    """One V3 detection with pixel box/polygon geometry and native order rank."""
    class_id: int
    label: str
    score: float
    box_px: tuple[float, float, float, float]
    polygon_px: tuple[tuple[float, float], ...]
    order: int | None
    contour_source: Literal["mask", "aabb_fallback", "legacy_unknown"] = "legacy_unknown"


@dataclass(frozen=True)
class LayoutPageResult:
    """One page's immutable pixel regions and runtime/model provenance."""
    page: int
    width_px: int
    height_px: int
    regions: tuple[LayoutRegion, ...]
    device: Device
    fallback_reason: FallbackReason | None
    model_id: str = MODEL_ID
    revision: str = REVISION
    engine: str = "onnxruntime"
    order_base: int = 0
    execution_failures: tuple[str, ...] = ()


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
    """Validate associated decoded arrays, allowing native rank gaps and ties."""
    try:
        scores, labels, boxes, orders = [
            output[key].tolist() for key in ("scores", "labels", "boxes", "order_seq")
        ]
        polygons = output["polygon_points"]
        sources = output.get("contour_sources", ["legacy_unknown"] * len(polygons))
        if len({len(v) for v in (scores, labels, boxes, orders, polygons, sources)}) != 1:
            raise ValueError("Inconsistent output lengths")
        if orders != sorted(orders) or any(type(rank) is not int or not 0 <= rank < 300 for rank in orders):
            raise ValueError("Invalid reading-order ranks")
        regions = []
        for score, label, box, polygon, order, source in zip(scores, labels, boxes, polygons, orders, sources):
            if source not in ("mask", "aabb_fallback", "legacy_unknown"):
                raise ValueError("Invalid contour provenance")
            if type(label) is not int or not 0 <= label < len(LABELS):
                raise ValueError("Unknown class")
            points = polygon.tolist() if polygon is not None else []
            if not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError("Invalid score")
            if len(box) != 4 or not all(math.isfinite(v) for v in box):
                raise ValueError("Invalid box")
            x0, y0, x1, y1 = box
            if not (max(0, x0) < min(width, x1) and max(0, y0) < min(height, y1)):
                raise ValueError("Box does not intersect the page")
            # Contour availability/validity is handled per region during conversion;
            # it must not discard a valid box, class, confidence or native rank.
            if not isinstance(points, list) or any(not isinstance(point, (list, tuple)) for point in points):
                raise ValueError("Malformed contour array")
            regions.append(LayoutRegion(label, LABELS[label], float(score), tuple(box),
                                        tuple(tuple(point) for point in points), order, source))
        return tuple(regions)
    except Exception as exc:
        raise LayoutInferenceError("invalid_output") from exc


def _decode_onnx(outputs, width: int, height: int) -> tuple[LayoutRegion, ...]:
    """Consume all exported outputs with one shared selection/order index."""
    import numpy as np
    from src.layout_polygons import extract_polygon_points_by_masks
    try:
        boxes, counts, masks = outputs
        if (boxes.ndim != 2 or boxes.shape[1] != 7 or counts.shape != (1,)
                or counts.dtype.kind not in "iu" or int(counts[0]) != len(boxes)
                or len(boxes) > 300 or masks.shape != (len(boxes), 200, 200)
                or masks.dtype.kind not in "iu" or not np.isin(masks, (0, 1)).all()
                or not np.isfinite(boxes).all()):
            raise ValueError("Malformed exported outputs")
        if ((boxes[:, 0] != np.floor(boxes[:, 0])).any()
                or (boxes[:, 6] != np.floor(boxes[:, 6])).any()
                or ((boxes[:, 0] < 0) | (boxes[:, 0] >= len(LABELS))).any()
                or ((boxes[:, 1] < 0) | (boxes[:, 1] > 1)).any()
                or ((boxes[:, 6] < 0) | (boxes[:, 6] >= 300)).any()):
            raise ValueError("Invalid class, confidence or native order")
        selected = np.flatnonzero(boxes[:, 1] > DETECTION_THRESHOLD)
        selected = selected[np.argsort(boxes[selected, 6], kind="stable")]
        boxes, masks = boxes[selected], masks[selected]
        if not len(boxes):
            return ()
        contour_boxes = boxes.copy()
        contour_boxes[:, 2:6] = np.round(contour_boxes[:, 2:6])
        sources = []
        polygons = extract_polygon_points_by_masks(
            contour_boxes, masks, (800 / width, 800 / height), "poly", sources=sources,
        )
        return _regions(dict(scores=boxes[:, 1], labels=boxes[:, 0].astype(np.int64),
                             boxes=boxes[:, 2:6], order_seq=boxes[:, 6].astype(np.int64),
                             polygon_points=polygons, contour_sources=sources), width, height)
    except LayoutInferenceError:
        raise
    except Exception as exc:
        raise LayoutInferenceError("invalid_output") from exc


class _OnnxBackend:
    def __init__(self, directory: Path):
        try:
            import onnxruntime as ort
            import numpy as np
            import cv2
        except (ImportError, OSError) as exc:
            raise LayoutModelUnavailable("dependencies_unavailable") from exc
        self.ort, self.np, self.cv2 = ort, np, cv2
        self.path = directory / "inference.onnx"
        self.session = None
        self._device: Device = "cpu"

    @property
    def device(self) -> Device:
        return self._device

    def cuda_available(self) -> bool:
        return "CUDAExecutionProvider" in self.ort.get_available_providers()

    def use_device(self, device: Device) -> None:
        self.session = None
        if device == "cuda":
            self.ort.preload_dlls(directory="")
        options = self.ort.SessionOptions()
        options.add_session_config_entry("session.record_ep_graph_assignment_info", "1")
        provider = "CUDAExecutionProvider" if device == "cuda" else "CPUExecutionProvider"
        session = self.ort.InferenceSession(str(self.path), sess_options=options, providers=[provider])
        session.disable_fallback()
        if provider not in session.get_providers():
            raise RuntimeError("Requested execution provider unavailable")
        if device == "cuda":
            assignments = session.get_provider_graph_assignment_info()
            if not any(item.ep_name == provider for item in assignments):
                raise RuntimeError("No graph nodes assigned to CUDA")
        self.session, self._device = session, device

    def predict(self, image: Image.Image) -> tuple[LayoutRegion, ...]:
        np, cv2 = self.np, self.cv2
        # Official RGB cubic 800x800 stretch, scale 1/255, mean 0, std 1, CHW.
        pixels = cv2.resize(np.asarray(image.convert("RGB")), (800, 800), interpolation=cv2.INTER_CUBIC)
        # Match upstream float32 multiplication (division differs by one ULP).
        pixels = np.ascontiguousarray((pixels.astype(np.float32) * (1.0 / 255.0)).transpose(2, 0, 1)[None])
        inputs = dict(image=pixels, im_shape=np.array([[800, 800]], dtype=np.float32),
                      scale_factor=np.array([[800 / image.height, 800 / image.width]], dtype=np.float32))
        from onnxruntime.capi.onnxruntime_pybind11_state import EPFail, RuntimeException, Fail, InvalidArgument
        try:
            outputs = self.session.run(["fetch_name_0", "fetch_name_1", "fetch_name_2"], inputs)
        except (EPFail, RuntimeException, Fail) as exc:
            raise LayoutExecutionError("inference_failed", device=self.device) from exc
        except InvalidArgument as exc:
            raise LayoutInferenceError("invalid_input", device=self.device) from exc
        return _decode_onnx(outputs, image.width, image.height)


class LayoutRuntime:
    """Lazy, serialized predictor with injected model resolution and backend."""
    def __init__(self, config: LayoutConfig | None = None, *,
                 snapshot_resolver: Callable[[LayoutConfig], Path] = resolve_model_snapshot,
                 backend_factory: Callable[[Path], LayoutBackend] = _OnnxBackend):
        self.config = config if config is not None else layout_config()
        self._resolve = snapshot_resolver
        self._factory = backend_factory
        self._backend: LayoutBackend | None = None
        self._fallback_reason = None
        self._terminal_failure: LayoutInferenceError | None = None
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
            if self._terminal_failure is not None:
                raise LayoutInferenceError("recovery_unavailable", failures=self._terminal_failure.failures,
                                           fallback_reason="cuda_execution_failed")
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
            if self._terminal_failure is not None:
                raise LayoutInferenceError("recovery_unavailable", failures=self._terminal_failure.failures,
                                           fallback_reason="cuda_execution_failed")
            backend = self._backend if self._backend is not None else self._initialize()
            failures = ()
            rgb = image.convert("RGB")
            try:
                regions = backend.predict(rgb)
                device = backend.device
            except LayoutExecutionError as exc:
                if self.config.device != "auto" or backend.device != "cuda":
                    raise LayoutInferenceError("inference_failed", device=backend.device,
                                               failures=(f"{backend.device}_execution",),
                                               fallback_reason=self._fallback_reason) from exc
                # Latch before recovery: no later page may probe CUDA again.
                self._fallback_reason = "cuda_execution_failed"
                failures = ("cuda_execution",)
                try:
                    backend.use_device("cpu")
                    if backend.device != "cpu":
                        raise RuntimeError("CPU placement was not honored")
                    backend.predict(Image.new("RGB", (96, 128), "white"))
                    if backend.device != "cpu":
                        raise RuntimeError("CPU probe changed device")
                except Exception as recovery:
                    self._terminal_failure = LayoutInferenceError(
                        "inference_failed", device="cuda", failures=failures + ("cpu_preparation",),
                        fallback_reason="cuda_execution_failed",
                    )
                    raise self._terminal_failure from recovery
                try:
                    regions = backend.predict(rgb)
                    device = backend.device
                except Exception as recovery:
                    code = recovery.code if isinstance(recovery, LayoutInferenceError) else "inference_failed"
                    stage = "cpu_execution" if isinstance(recovery, LayoutExecutionError) else "cpu_validation"
                    raise LayoutInferenceError(code, device="cpu", failures=failures + (stage,),
                                               fallback_reason="cuda_execution_failed") from recovery
            except LayoutInferenceError as exc:
                exc.device = backend.device
                exc.fallback_reason = self._fallback_reason
                raise
            except Exception as exc:
                raise LayoutInferenceError("inference_failed", device=backend.device,
                                           fallback_reason=self._fallback_reason) from exc
            return LayoutPageResult(page_number, image.width, image.height, regions,
                                    device, self._fallback_reason, execution_failures=failures)


_singleton: LayoutRuntime | None = None
_singleton_lock = RLock()


def get_layout_runtime() -> LayoutRuntime:
    """One runtime per process; restart the process to change configuration."""
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = LayoutRuntime()
        return _singleton
