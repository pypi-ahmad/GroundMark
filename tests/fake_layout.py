"""Explicit offline runtime and image fixtures; no inference dependencies."""
import base64
import io

from PIL import Image

from src.layout_detector import LayoutPageResult, LayoutReadiness


def payload(page=1, width=100, height=100, color="white", sha="synthetic"):
    with Image.new("RGB", (width, height), color) as image, io.BytesIO() as data:
        image.save(data, format="PNG")
        return dict(page=page, width=width, height=height, mime="image/png",
                    base64=base64.b64encode(data.getvalue()).decode("ascii"), doc_sha256=sha)


class FakeLayoutRuntime:
    def __init__(self, *, regions=None, failures=None, initialization_error=None, events=None):
        self.regions = regions or {}
        self.failures = failures or {}
        self.initialization_error = initialization_error
        self.events = events if events is not None else []
        self.images = {}
        self.ready = False

    def prepare(self):
        self.events.append(("prepare",))
        if self.initialization_error is not None:
            raise self.initialization_error
        reused = self.ready
        self.ready = True
        return LayoutReadiness("cpu", None, 0.0, reused)

    def predict(self, image, page_number=1):
        self.events.append(("v3", page_number))
        self.images[page_number] = (image.size, image.convert("RGB").tobytes())
        if page_number in self.failures:
            raise self.failures[page_number]
        return LayoutPageResult(page_number, image.width, image.height,
                                tuple(self.regions.get(page_number, ())), "cpu", None)
