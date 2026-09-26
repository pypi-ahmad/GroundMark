"""Opt-in fakes and a guard against accidental native inference in unit tests."""
import pytest

from tests.fake_layout import FakeLayoutRuntime


@pytest.fixture(autouse=True)
def forbid_native_layout_initialization(monkeypatch):
    from src import layout_detector
    initialize = layout_detector.LayoutRuntime._initialize

    def guarded(runtime):
        if runtime._factory is layout_detector._TransformersBackend:
            pytest.fail("Offline tests must inject a layout runtime/backend before model resolution")
        return initialize(runtime)

    monkeypatch.setattr(layout_detector.LayoutRuntime, "_initialize", guarded)


@pytest.fixture
def fake_layout_runtime(monkeypatch):
    from src import parse
    from src import layout_detector
    runtime = FakeLayoutRuntime()
    monkeypatch.setattr(parse, "get_layout_runtime", lambda: runtime)
    monkeypatch.setattr(layout_detector, "get_layout_runtime", lambda: runtime)
    return runtime
