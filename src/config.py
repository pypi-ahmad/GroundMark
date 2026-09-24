"""Validated security limits shared by CLI, UI, and model clients."""

from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlsplit


class ConfigError(ValueError):
    pass


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
    return _positive_int("GROUNDMARK_MAX_SOURCE_MIB", 100)


def max_source_bytes() -> int:
    return max_source_mib() * 1024 * 1024


def max_pages() -> int:
    return _positive_int("GROUNDMARK_MAX_PAGES", 250)


def max_image_pixels() -> int:
    return _positive_int("GROUNDMARK_MAX_IMAGE_PIXELS", 50_000_000)


def max_parse_output_tokens() -> int:
    return _positive_int("GROUNDMARK_MAX_PARSE_OUTPUT_TOKENS", 16_384)


def max_table_cells() -> int:
    return _positive_int("GROUNDMARK_MAX_TABLE_CELLS", 10_000)


def max_figures() -> int:
    return _positive_int("GROUNDMARK_MAX_FIGURES", 128)


def max_figure_bytes() -> int:
    return _positive_int("GROUNDMARK_MAX_FIGURE_MIB", 32) * 1024 * 1024


def is_loopback_host(host: str) -> bool:
    if host.strip().casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip().strip("[]")).is_loopback
    except ValueError:
        return False


def validate_loopback_host(host: str) -> str:
    if not is_loopback_host(host):
        raise ConfigError("GroundMark UI may only bind to localhost or a loopback IP address")
    return host


def validated_openai_base_url() -> str | None:
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
