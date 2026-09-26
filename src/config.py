"""Validated security limits shared by CLI, UI, and model clients."""

from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit


class ConfigError(ValueError):
    """An invalid environment setting or unsupported local server address."""
    pass


@dataclass(frozen=True)
class LayoutConfig:
    """V3 device policy and optional verified local model directory."""
    device: Literal["auto", "cpu"] = "auto"
    model_dir: Path | None = None


def layout_config() -> LayoutConfig:
    """Read only when the standalone layout runtime is requested."""
    device = os.environ.get("GROUNDMARK_LAYOUT_DEVICE", "auto").strip()
    if device not in {"auto", "cpu"}:
        raise ConfigError("GROUNDMARK_LAYOUT_DEVICE must be auto or cpu")
    raw = os.environ.get("GROUNDMARK_LAYOUT_MODEL_DIR")
    directory = None
    if raw is not None:
        try:
            if not raw.strip():
                raise ValueError("Empty path")
            directory = Path(raw.strip()).expanduser().resolve(strict=True)
            if not directory.is_dir():
                raise ValueError("Not a directory")
        except (OSError, ValueError, RuntimeError) as exc:
            raise ConfigError("GROUNDMARK_LAYOUT_MODEL_DIR must name an existing local directory") from exc
    return LayoutConfig(device=device, model_dir=directory)


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a positive integer") from exc
    if value < 1:
        raise ConfigError(f"{name} must be a positive integer")
    return value


def max_source_mib() -> int:
    """Return the positive source-size limit in MiB; invalid settings raise ConfigError."""
    return _positive_int("GROUNDMARK_MAX_SOURCE_MIB", 100)


def max_source_bytes() -> int:
    """Return the configured source-size limit converted from MiB to bytes."""
    return max_source_mib() * 1024 * 1024


def max_pages() -> int:
    """Return the positive selected-page limit; invalid settings raise ConfigError."""
    return _positive_int("GROUNDMARK_MAX_PAGES", 250)


def max_image_pixels() -> int:
    """Return the positive raster pixel limit; invalid settings raise ConfigError."""
    return _positive_int("GROUNDMARK_MAX_IMAGE_PIXELS", 50_000_000)


def max_parse_output_tokens() -> int:
    """Return the positive Sol output-token cap; invalid settings raise ConfigError."""
    return _positive_int("GROUNDMARK_MAX_PARSE_OUTPUT_TOKENS", 16_384)


def max_table_cells() -> int:
    """Return the positive expanded-table cell budget; invalid settings raise ConfigError."""
    return _positive_int("GROUNDMARK_MAX_TABLE_CELLS", 10_000)


def max_figures() -> int:
    """Return the positive retained-figure count limit; invalid settings raise ConfigError."""
    return _positive_int("GROUNDMARK_MAX_FIGURES", 128)


def max_figure_bytes() -> int:
    """Return the retained-figure byte budget; invalid MiB settings raise ConfigError."""
    return _positive_int("GROUNDMARK_MAX_FIGURE_MIB", 32) * 1024 * 1024


def is_loopback_host(host: str) -> bool:
    """Return whether the stripped host names localhost or a loopback IP."""
    if host.strip().casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip().strip("[]")).is_loopback
    except ValueError:
        return False


def validate_loopback_host(host: str) -> str:
    """Return the supplied host, or raise ConfigError for a non-loopback bind."""
    if not is_loopback_host(host):
        raise ConfigError("GroundMark UI may only bind to localhost or a loopback IP address")
    return host


def validated_openai_base_url() -> str | None:
    """Read OPENAI_BASE_URL; return None for blank or the validated URL.

    Reject credentials, queries, fragments, and non-HTTPS remote endpoints with
    ConfigError. HTTP is accepted only for loopback hosts.
    """
    raw = os.environ.get("OPENAI_BASE_URL", "").strip()
    if not raw:
        return None
    parsed = urlsplit(raw)
    if (not parsed.hostname or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment):
        raise ConfigError("OPENAI_BASE_URL must not contain credentials, a query, or a fragment")
    if parsed.scheme == "https":
        return raw
    if parsed.scheme == "http" and is_loopback_host(parsed.hostname):
        return raw
    raise ConfigError("OPENAI_BASE_URL must use HTTPS, except for loopback HTTP endpoints")
