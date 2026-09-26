"""Allowlisted API metadata; response text never enters diagnostics.

Every field on `PageDiagnostic`/`FilterAnnotation` is either a bounded
literal, a count, or a value that passed `safe_identifier`'s allowlist --
never raw provider text, headers, or request/response bodies. Must not: gain
a free-text field (e.g. a raw error message) without also redacting it --
that would defeat the point of this module, since `PageDiagnostic` is shown
directly in the UI (see src/ui/app.py's "API diagnostics" expander) and may
be persisted in ParseResult JSON.

Next: src/llm.py's `_invoke_structured`, where these fields are
populated from a real (or mocked) API response.
"""

import os
import re
from typing import Literal, get_args

from pydantic import BaseModel, Field


class FilterAnnotation(BaseModel):
    source: Literal["prompt", "completion"]
    category: Literal["hate", "sexual", "violence", "self_harm", "jailbreak"]
    filtered: bool | None = None
    severity: Literal["safe", "low", "medium", "high"] | None = None


LayoutStage = Literal["initialization", "inference", "conversion", "prompt", "reconciliation"]
LayoutCode = Literal[
    "dependencies_unavailable", "download_failed", "invalid_model", "model_load_failed", "devices_failed",
    "invalid_configuration", "invalid_image", "inference_failed", "invalid_output", "invalid_page",
    "invalid_order_base", "invalid_class", "invalid_score", "invalid_order", "invalid_box", "invalid_polygon",
    "page_mismatch", "invalid_normalized_region", "layout_prompt_too_large", "unexpected_layout_error",
]


class PageDiagnostic(BaseModel):
    page: int | None = None
    outcome: Literal["parsed", "content_filtered", "refused", "incomplete", "invalid_response", "http_error", "transport_error", "layout_unavailable", "layout_failed"] = "invalid_response"
    layout_stage: LayoutStage | None = None
    layout_code: LayoutCode | None = None
    layout_fallback: bool = False
    layout_device: Literal["cpu", "cuda"] | None = None
    layout_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    page_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    http_status: int | None = None
    request_id: str | None = None
    model: str | None = None
    requested_model: str | None = None
    finish_reason: Literal["stop", "length", "content_filter", "tool_calls", "function_call"] | None = None
    usage_known: bool = False
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    cache_write_tokens: int | None = None
    filters: list[FilterAnnotation] = Field(default_factory=list)


class ExtractionCallError(Exception):
    """A failed extraction call carrying a safe PageDiagnostic."""
    def __init__(self, diagnostic: PageDiagnostic):
        self.diagnostic = diagnostic
        super().__init__(f"Extraction request failed: {diagnostic.outcome}")


def layout_failure_diagnostic(exc: Exception, *, page: int, stage: LayoutStage,
                              requested_model: str, previous: PageDiagnostic | None = None) -> PageDiagnostic:
    """Map local failures to allowlisted metadata, retaining any paid-call usage."""
    from src.config import ConfigError
    from src.layout_detector import LayoutModelUnavailable
    code = "invalid_configuration" if isinstance(exc, ConfigError) else getattr(exc, "code", None)
    if not isinstance(code, str) or code not in get_args(LayoutCode):
        code = "unexpected_layout_error"
    if isinstance(exc, (LayoutModelUnavailable, ConfigError)):
        stage = "initialization"
    baseline = previous or PageDiagnostic(requested_model=requested_model)
    return baseline.model_copy(update=dict(
        page=page, outcome="layout_unavailable" if stage == "initialization" else "layout_failed",
        layout_stage=stage, layout_code=code,
    ))


def layout_failure_summary(diagnostic: PageDiagnostic) -> str:
    """Actionable display text generated only from validated codes."""
    summary = f"Page {diagnostic.page}: {diagnostic.outcome} ({diagnostic.layout_stage}: {diagnostic.layout_code})"
    if diagnostic.outcome == "layout_unavailable":
        from src.layout_detector import LayoutModelUnavailable
        if diagnostic.layout_code in {"dependencies_unavailable", "download_failed", "invalid_model", "model_load_failed", "devices_failed"}:
            return f"{summary}. {LayoutModelUnavailable(diagnostic.layout_code)}"
        return f"{summary}. Check GROUNDMARK_LAYOUT_DEVICE, GROUNDMARK_LAYOUT_MODEL_DIR and the layout installation."
    return summary


def layout_ready_summary(info: dict) -> str:
    """Shared UI/CLI readiness message from the runtime's local summary."""
    device = "GPU (CUDA)" if info["device"] == "cuda" else "CPU"
    mode = "reused" if info["reused"] else "prepared"
    text = f"PP-DocLayoutV3 ready: {device}; {mode} in {info['preparation_seconds']:.3f}s."
    fallback = {"cuda_unavailable": "CUDA unavailable; verified CPU fallback.",
                "cuda_probe_failed": "CUDA probe failed; verified CPU fallback."}.get(info.get("fallback_reason"))
    return f"{text} {fallback}" if fallback else text


def safe_identifier(value) -> str | None:
    # Three independent layers, any of which can veto the value: (1) shape --
    # short, plain-token-looking strings only, which already excludes most
    # free-form provider text; (2) known secret-ish substrings/URLs, in case
    # something token-shaped still looks like a credential; (3) a literal
    # match against any currently-configured secret-like env var value, so an
    # actual configured key never echoes back even if it doesn't match (2).
    """Return an allowlisted identifier, or None for unsafe/non-string input.

    Reject free text, URLs, credential-like patterns, and matches to configured
    secret values. The returned value may be persisted in diagnostics.
    """
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", value):
        return None
    if re.search(r"(?i)(sk-|bearer|api.key|token=)", value) or "://" in value:
        return None
    if any(secret and len(secret) >= 8 and secret in value for name, secret in os.environ.items()
           if any(part in name.upper() for part in ("KEY", "TOKEN", "SECRET", "PASSWORD"))):
        return None
    return value


def token_count(value) -> int | None:
    # `type(value) is int` (not isinstance) deliberately excludes bool: bool
    # is an int subclass in Python, and a stray True/False from a malformed
    # response body must not be reported as a token count of 1/0.
    """Return a nonnegative integer count or None; booleans are not counts."""
    return value if type(value) is int and value >= 0 else None


def filter_annotations(data, source: Literal["prompt", "completion"]) -> list[FilterAnnotation]:
    """Extract recognized category annotations from a provider metadata dictionary.

    Return FilterAnnotation objects with bounded source/category/severity fields;
    ignore malformed and unknown entries without retaining raw response text.
    """
    if not isinstance(data, dict):
        return []
    results = []
    for category in ("hate", "sexual", "violence", "self_harm", "jailbreak"):
        item = data.get(category)
        if not isinstance(item, dict):
            continue
        filtered = item.get("filtered") if type(item.get("filtered")) is bool else None
        severity = item.get("severity") if item.get("severity") in ("safe", "low", "medium", "high") else None
        if filtered is not None or severity is not None:
            results.append(FilterAnnotation(source=source, category=category, filtered=filtered, severity=severity))
    return results
