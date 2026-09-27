"""Standalone layout tests: injected backends, no weights, downloads, or Sol."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import subprocess
import sys

from PIL import Image
import pytest

from src import layout_detector as detector
from src.config import ConfigError, LayoutConfig, layout_config


class FakeBackend:
    def __init__(self, *, available=True, fail_move=(), fail_probe=(), ignore_cuda=False):
        self.device = "cpu"
        self.available = available
        self.fail_move = fail_move
        self.fail_probe = fail_probe
        self.ignore_cuda = ignore_cuda
        self.moves = []
        self.calls = []

    def cuda_available(self):
        return self.available

    def use_device(self, device):
        self.moves.append(device)
        if device in self.fail_move:
            raise RuntimeError("private native detail")
        if not (device == "cuda" and self.ignore_cuda):
            self.device = device

    def predict(self, image):
        self.calls.append((self.device, image.size))
        if image.size == (96, 128) and self.device in self.fail_probe:
            raise RuntimeError("private native detail")
        return ()


def runtime(backend, config=None):
    resolutions, loads = [], []
    predictor = detector.LayoutRuntime(
        config or LayoutConfig(),
        snapshot_resolver=lambda config: resolutions.append(config) or Path("injected-snapshot"),
        backend_factory=lambda directory: loads.append(directory) or backend,
    )
    return predictor, resolutions, loads


def image():
    return Image.new("RGB", (100, 200), "white")


def test_lazy_initialization_and_single_model_reuse():
    backend = FakeBackend()
    predictor, resolutions, loads = runtime(backend)
    assert not resolutions and not loads and not backend.calls
    first = predictor.predict(image(), 2)
    second = predictor.predict(image(), 3)
    assert len(resolutions) == len(loads) == 1
    assert backend.calls == [("cuda", (96, 128)), ("cuda", (100, 200)), ("cuda", (100, 200))]
    assert first.page == 2 and second.page == 3
    assert first.width_px == 100 and first.height_px == 200
    assert first.device == "cuda" and first.fallback_reason is None
    assert first.model_id == detector.MODEL_ID and first.revision == detector.REVISION


def test_prepare_probes_once_without_analyzing_a_document_page():
    backend = FakeBackend()
    predictor, resolutions, loads = runtime(backend)
    first = predictor.prepare()
    second = predictor.prepare()
    assert first.device == second.device == "cuda" and first.fallback_reason is None
    assert not first.reused and second.reused
    assert first.preparation_seconds >= 0 and second.preparation_seconds >= 0
    assert backend.calls == [("cuda", (96, 128))]
    predictor.predict(image())
    assert backend.calls == [("cuda", (96, 128)), ("cuda", (100, 200))]
    assert len(resolutions) == len(loads) == 1


@pytest.mark.parametrize("options,reason", [
    (dict(available=False), "cuda_unavailable"),
    (dict(fail_move={"cuda"}), "cuda_probe_failed"),
    (dict(fail_probe={"cuda"}), "cuda_probe_failed"),
    (dict(ignore_cuda=True), "cuda_probe_failed"),
])
def test_gpu_to_cpu_fallback_requires_successful_cpu_probe(options, reason):
    backend = FakeBackend(**options)
    predictor, _, loads = runtime(backend)
    result = predictor.predict(image())
    assert result.device == "cpu" and result.fallback_reason == reason
    assert backend.calls[-2:] == [("cpu", (96, 128)), ("cpu", (100, 200))]
    assert len(loads) == 1
    ready = predictor.prepare()
    assert ready.device == "cpu" and ready.fallback_reason == reason and ready.reused


def test_cpu_mode_does_not_even_query_cuda():
    backend = FakeBackend()
    backend.cuda_available = lambda: pytest.fail("CPU mode queried CUDA")
    predictor, _, _ = runtime(backend, LayoutConfig(device="cpu"))
    result = predictor.predict(image())
    assert result.device == "cpu" and result.fallback_reason is None
    assert backend.moves == ["cpu"]


@pytest.mark.parametrize("available,attempted", [(True, ("cuda", "cpu")), (False, ("cpu",))])
def test_cpu_failure_is_typed_actionable_and_not_cached(available, attempted):
    backend = FakeBackend(available=available, fail_probe={"cuda", "cpu"})
    predictor, _, _ = runtime(backend)
    with pytest.raises(detector.LayoutModelUnavailable) as caught:
        predictor.predict(image())
    assert caught.value.code == "devices_failed"
    assert caught.value.attempted_devices == attempted
    assert "private" not in str(caught.value) and "memory" in str(caught.value)
    assert predictor._backend is None
    assert all(size == (96, 128) for _, size in backend.calls)


def test_missing_dependencies_are_typed_and_actionable():
    def missing(path):
        raise ModuleNotFoundError("private path")
    predictor = detector.LayoutRuntime(LayoutConfig(), snapshot_resolver=lambda config: Path("snapshot"),
                                       backend_factory=missing)
    with pytest.raises(detector.LayoutModelUnavailable, match="uv sync --extra layout") as caught:
        predictor.predict(image())
    assert caught.value.code == "dependencies_unavailable"


def test_singleton_and_concurrent_first_predictions(monkeypatch):
    backend = FakeBackend()
    predictor, resolutions, loads = runtime(backend)
    created = []
    monkeypatch.setattr(detector, "_singleton", None)
    monkeypatch.setattr(detector, "LayoutRuntime", lambda: created.append(1) or predictor)
    with ThreadPoolExecutor(max_workers=4) as pool:
        instances = list(pool.map(lambda _: detector.get_layout_runtime(), range(8)))
        results = list(pool.map(lambda instance: instance.predict(image()), instances))
    assert all(instance is predictor for instance in instances)
    assert len(created) == len(resolutions) == len(loads) == 1
    assert len(results) == 8 and len(backend.calls) == 9


def test_page_failure_does_not_retry_cpu():
    backend = FakeBackend()
    predictor, _, _ = runtime(backend)
    predictor.predict(image())
    def fail(image):
        raise RuntimeError("private document content")
    backend.predict = fail
    with pytest.raises(detector.LayoutInferenceError, match="inference_failed") as caught:
        predictor.predict(image())
    assert backend.moves == ["cuda"] and "private" not in str(caught.value)


@pytest.fixture
def snapshot(tmp_path, monkeypatch):
    # Small fake files exercise resolution/checksums, not model loading.
    files = {"inference.yml": b"fixture config", "inference.onnx": b"fixture weights"}
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    monkeypatch.setattr(detector, "MODEL_FILES", hashes)
    def populate():
        for name, data in files.items():
            (tmp_path / name).write_bytes(data)
    return tmp_path, populate


def test_first_use_download_then_disk_cache_reuse(snapshot):
    directory, populate = snapshot
    calls = []
    def downloader(**kwargs):
        calls.append(kwargs)
        if kwargs["local_files_only"] and not (directory / "inference.yml").exists():
            raise FileNotFoundError("cold cache")
        if not kwargs["local_files_only"]:
            populate()
        return str(directory)
    assert detector.resolve_model_snapshot(LayoutConfig(), downloader=downloader) == directory
    assert [call["local_files_only"] for call in calls] == [True, False]
    assert all(call["repo_id"] == detector.MODEL_ID and call["revision"] == detector.REVISION for call in calls)
    assert all(set(call["allow_patterns"]) == set(detector.MODEL_FILES) for call in calls)
    # No local_dir/cache_dir: respect the Hub's ordinary user-cache configuration.
    assert all("local_dir" not in call and "cache_dir" not in call for call in calls)
    calls.clear()
    assert detector.resolve_model_snapshot(LayoutConfig(), downloader=downloader) == directory
    assert [call["local_files_only"] for call in calls] == [True]


def test_partial_cache_downloads_missing_files(snapshot):
    directory, populate = snapshot
    (directory / "inference.yml").write_bytes(b"fixture config")
    calls = []
    def downloader(**kwargs):
        calls.append(kwargs["local_files_only"])
        if not kwargs["local_files_only"]:
            populate()
        return directory
    detector.resolve_model_snapshot(LayoutConfig(), downloader=downloader)
    assert calls == [True, False]


def test_local_directory_never_downloads_and_rejects_wrong_files(snapshot):
    directory, populate = snapshot
    populate()
    def forbidden(**kwargs):
        pytest.fail("Local override tried to download")
    assert detector.resolve_model_snapshot(LayoutConfig(model_dir=directory), downloader=forbidden) == directory
    (directory / "inference.onnx").write_bytes(b"not the pinned model")
    with pytest.raises(detector.LayoutModelUnavailable, match="invalid_model"):
        detector.resolve_model_snapshot(LayoutConfig(model_dir=directory), downloader=forbidden)


def test_unreachable_first_use_is_typed():
    def offline(**kwargs):
        raise ConnectionError("secret endpoint")
    with pytest.raises(detector.LayoutModelUnavailable, match="connectivity") as caught:
        detector.resolve_model_snapshot(LayoutConfig(), downloader=offline)
    assert caught.value.code == "download_failed" and "secret" not in str(caught.value)


@pytest.mark.parametrize("value", ["", "gpu", "cuda", "AUTO", "false"])
def test_invalid_device_config(monkeypatch, value):
    monkeypatch.setenv("GROUNDMARK_LAYOUT_DEVICE", value)
    with pytest.raises(ConfigError, match="auto or cpu"):
        layout_config()


def test_local_config_validation(tmp_path, monkeypatch):
    monkeypatch.delenv("GROUNDMARK_LAYOUT_DEVICE", raising=False)
    monkeypatch.delenv("GROUNDMARK_LAYOUT_MODEL_DIR", raising=False)
    assert layout_config() == LayoutConfig()
    monkeypatch.setenv("GROUNDMARK_LAYOUT_MODEL_DIR", str(tmp_path))
    assert layout_config().model_dir == tmp_path
    for value in ("", str(tmp_path / "missing")):
        monkeypatch.setenv("GROUNDMARK_LAYOUT_MODEL_DIR", value)
        with pytest.raises(ConfigError, match="existing local directory"):
            layout_config()


def test_base_imports_do_not_load_optional_dependencies():
    code = """
import importlib.abc, sys
class BlockOptional(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'torchvision', 'transformers', 'huggingface_hub', 'cv2', 'onnxruntime'}:
            raise ModuleNotFoundError(fullname)
sys.meta_path.insert(0, BlockOptional())
import src, src.cli, src.parse, src.graph, src.markdown, src.layout_detector
assert src.layout_detector._singleton is None
from src.config import LayoutConfig
try:
    src.layout_detector.resolve_model_snapshot(LayoutConfig())
except src.layout_detector.LayoutModelUnavailable as exc:
    assert exc.code == 'dependencies_unavailable'
else:
    raise AssertionError('Missing dependency was not diagnosed')
"""
    result = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


class Array:
    def __init__(self, values): self.values = values
    def detach(self): return self
    def cpu(self): return self
    def tolist(self): return self.values


def test_postprocessor_adapter_retains_pixels_polygons_and_native_rank():
    output = dict(scores=Array([.9]), labels=Array([9]), boxes=Array([[-1, 2, 30, 40]]),
                  order_seq=Array([142]), polygon_points=[Array([[0, 2], [30, 2], [30, 40], [0, 40]])])
    region, = detector._regions(output, 100, 200)
    assert region.class_id == 9 and region.label == "footer_image"
    assert region.box_px == (-1, 2, 30, 40) and region.order == 142
    assert region.polygon_px[-1] == (0, 40)
    output["scores"] = Array([float("nan")])
    with pytest.raises(detector.LayoutInferenceError, match="invalid_output"):
        detector._regions(output, 100, 200)


def test_empty_detection_is_valid():
    output = {key: Array([]) for key in ("scores", "labels", "boxes", "order_seq")}
    output["polygon_points"] = []
    assert detector._regions(output, 100, 100) == ()


@pytest.mark.parametrize("page", [0, -1, True])
def test_invalid_page_does_not_initialize(page):
    backend = FakeBackend()
    predictor, resolutions, _ = runtime(backend)
    with pytest.raises(ValueError):
        predictor.predict(image(), page)
    assert not resolutions


class ExecutionBackend(FakeBackend):
    def __init__(self, *, cpu_failure=None):
        super().__init__()
        self.cpu_failure = cpu_failure

    def predict(self, image):
        super().predict(image)
        if image.size != (96, 128) and self.device == "cuda":
            raise detector.LayoutExecutionError("inference_failed", device="cuda")
        if self.device == "cpu" and self.cpu_failure:
            if self.cpu_failure == "prepare" or image.size != (96, 128):
                if self.cpu_failure == "validation":
                    raise detector.LayoutInferenceError("invalid_output")
                raise detector.LayoutExecutionError("inference_failed", device="cpu")
        return ()


def test_execution_recovery_retries_once_and_cpu_is_sticky():
    backend = ExecutionBackend()
    predictor, _, loads = runtime(backend)
    assert predictor.prepare().device == "cuda"
    recovered = predictor.predict(image())
    assert recovered.device == "cpu"
    assert recovered.execution_failures == ("cuda_execution",)
    assert recovered.fallback_reason == "cuda_execution_failed"
    later = predictor.predict(image(), 2)
    assert later.device == "cpu" and later.execution_failures == ()
    ready = predictor.prepare()
    assert ready.device == "cpu" and ready.reused
    assert ready.fallback_reason == "cuda_execution_failed"
    assert backend.moves == ["cuda", "cpu"] and len(loads) == 1
    assert backend.calls == [("cuda", (96, 128)), ("cuda", (100, 200)),
                             ("cpu", (96, 128)), ("cpu", (100, 200)), ("cpu", (100, 200))]


@pytest.mark.parametrize("failure,stage", [
    ("prepare", "cpu_preparation"), ("execute", "cpu_execution"), ("validation", "cpu_validation"),
])
def test_failed_recovery_reports_both_stages_without_cuda_reprobe(failure, stage):
    backend = ExecutionBackend(cpu_failure=failure)
    predictor, _, _ = runtime(backend)
    with pytest.raises(detector.LayoutInferenceError) as caught:
        predictor.predict(image())
    assert caught.value.failures == ("cuda_execution", stage)
    assert caught.value.device == ("cuda" if failure == "prepare" else "cpu")
    calls = len(backend.calls)
    with pytest.raises(detector.LayoutInferenceError) as later:
        predictor.predict(image(), 2)
    if failure == "prepare":
        assert later.value.code == "recovery_unavailable" and later.value.device is None
    assert backend.moves == ["cuda", "cpu"]
    assert len(backend.calls) == calls + (0 if failure == "prepare" else 1)


def test_invalid_decoding_does_not_trigger_device_recovery():
    backend = FakeBackend()
    predictor, _, _ = runtime(backend)
    predictor.prepare()
    def invalid(image):
        raise detector.LayoutInferenceError("invalid_output")
    backend.predict = invalid
    with pytest.raises(detector.LayoutInferenceError) as caught:
        predictor.predict(image())
    assert caught.value.code == "invalid_output" and caught.value.device == "cuda"
    assert backend.moves == ["cuda"]


def test_onnx_decoding_keeps_fields_masks_gaps_and_ties_associated(monkeypatch):
    np = pytest.importorskip("numpy")
    pytest.importorskip("cv2")
    from src import layout_polygons
    boxes = np.array([[9, .9, 10, 10, 50, 50, 142],
                      [2, .5, 20, 20, 60, 60, 0],
                      [22, .8, 30, 30, 70, 70, 3],
                      [21, .7, 40, 40, 80, 80, 3]], dtype=np.float32)
    masks = np.zeros((4, 200, 200), dtype=np.int32)
    for i in range(4):
        masks[i, i, i] = 1
    def polygons(selected, selected_masks, scale, mode, *, sources):
        sources.extend(["mask"] * len(selected))
        assert selected[:, 0].tolist() == [22, 21, 9]
        assert [int(np.flatnonzero(m)[0]) for m in selected_masks] == [402, 603, 0]
        assert scale == (8, 4) and mode == "poly"
        return [np.array([[x, y], [right, y], [right, bottom], [x, bottom]])
                for x, y, right, bottom in selected[:, 2:6]]
    monkeypatch.setattr(layout_polygons, "extract_polygon_points_by_masks", polygons)
    regions = detector._decode_onnx([boxes, np.array([4], dtype=np.int32), masks], 100, 200)
    assert [r.order for r in regions] == [3, 3, 142]
    assert [r.label for r in regions] == ["text", "table", "footer_image"]
    assert [r.score for r in regions] == pytest.approx([.8, .7, .9])
    assert regions[0].box_px == (30, 30, 70, 70)
    assert regions[0].polygon_px[0] == (30, 30)
    for invalid in ([boxes, np.array([3]), masks], [boxes, np.array([4]), masks.astype(float)]):
        with pytest.raises(detector.LayoutInferenceError, match="invalid_output"):
            detector._decode_onnx(invalid, 100, 200)


def test_upstream_mask_polygon_decode_and_empty_detection():
    np = pytest.importorskip("numpy")
    pytest.importorskip("cv2")
    boxes = np.array([[22, .9, 10, 10, 90, 90, 0]], dtype=np.float32)
    masks = np.zeros((1, 200, 200), dtype=np.int32)
    masks[0, 20:160, 20:70] = 1
    masks[0, 120:160, 20:160] = 1
    region, = detector._decode_onnx([boxes, np.array([1]), masks], 100, 100)
    assert len(region.polygon_px) >= 4 and region.order == 0
    empty = detector._decode_onnx([np.empty((0, 7)), np.array([0]), np.empty((0, 200, 200), dtype=np.int32)], 100, 100)
    assert empty == ()


def test_onnx_preprocessing_and_native_error_boundary(monkeypatch):
    np = pytest.importorskip("numpy")
    pytest.importorskip("cv2")
    pytest.importorskip("onnxruntime")
    from onnxruntime.capi.onnxruntime_pybind11_state import EPFail, InvalidArgument
    backend = detector._OnnxBackend(Path("unused"))
    received = []
    class Session:
        def run(self, names, inputs):
            received.append((names, inputs))
            return [np.empty((0, 7)), np.array([0]), np.empty((0, 200, 200), dtype=np.int32)]
    backend.session = Session()
    source = Image.new("RGB", (100, 200), (255, 128, 0))
    assert backend.predict(source) == ()
    names, inputs = received[0]
    assert names == ["fetch_name_0", "fetch_name_1", "fetch_name_2"]
    assert inputs["image"].shape == (1, 3, 800, 800)
    assert inputs["image"].dtype == np.float32 and inputs["image"].flags.c_contiguous
    assert inputs["image"][0, :, 0, 0].tolist() == pytest.approx([1, 128 / 255, 0])
    np.testing.assert_array_equal(inputs["image"][0, :, 0, 0],
                                  np.array([255, 128, 0], dtype=np.float32) * (1.0 / 255.0))
    assert inputs["im_shape"].tolist() == [[800, 800]]
    assert inputs["scale_factor"].tolist() == [[4, 8]]
    def fail(*a):
        raise EPFail("private native detail")
    monkeypatch.setattr(backend.session, "run", fail)
    with pytest.raises(detector.LayoutExecutionError):
        backend.predict(source)
    def invalid(*a):
        raise InvalidArgument("bad input")
    monkeypatch.setattr(backend.session, "run", invalid)
    with pytest.raises(detector.LayoutInferenceError, match="invalid_input") as caught:
        backend.predict(source)
    assert not isinstance(caught.value, detector.LayoutExecutionError)


def test_onnx_provider_must_be_present_and_have_actual_graph_assignment(monkeypatch):
    ort = pytest.importorskip("onnxruntime")
    from types import SimpleNamespace
    backend = detector._OnnxBackend(Path("unused"))
    preloads, fallback_disabled = [], []
    monkeypatch.setattr(ort, "preload_dlls", lambda **kw: preloads.append(kw))
    class Session:
        providers = ["CPUExecutionProvider"]
        assignments = []
        def __init__(self, *a, **kw): self.options = kw
        def disable_fallback(self): fallback_disabled.append(True)
        def get_providers(self): return self.providers
        def get_provider_graph_assignment_info(self): return self.assignments
    monkeypatch.setattr(ort, "InferenceSession", Session)
    with pytest.raises(RuntimeError, match="provider unavailable"):
        backend.use_device("cuda")
    Session.providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    with pytest.raises(RuntimeError, match="No graph nodes"):
        backend.use_device("cuda")
    Session.assignments = [SimpleNamespace(ep_name="CUDAExecutionProvider")]
    backend.use_device("cuda")
    assert backend.device == "cuda" and len(preloads) == 3 and len(fallback_disabled) == 3
    previous = backend.session
    Session.providers = ["CPUExecutionProvider"]
    backend.use_device("cpu")
    assert backend.session is not previous and backend.device == "cpu"
    assert backend.session.options["providers"] == ["CPUExecutionProvider"] and len(preloads) == 3
