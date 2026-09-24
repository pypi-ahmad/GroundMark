import pytest

from src.config import ConfigError, max_pages, validated_openai_base_url, validate_loopback_host


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "::1", "[::1]"])
def test_ui_host_accepts_only_loopback(host):
    assert validate_loopback_host(host) == host


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.1.2", "example.com"])
def test_ui_host_rejects_non_loopback(host):
    with pytest.raises(ConfigError):
        validate_loopback_host(host)


@pytest.mark.parametrize("url", ["https://api.example.com/v1", "http://localhost:8000/v1",
                                  "http://127.0.0.1:8000/v1", "http://[::1]:8000/v1"])
def test_base_url_accepts_https_or_loopback_http(monkeypatch, url):
    monkeypatch.setenv("OPENAI_BASE_URL", url)
    assert validated_openai_base_url() == url


@pytest.mark.parametrize("url", ["http://api.example.com/v1", "ftp://example.com/v1",
                                  "https://user:pass@example.com/v1", "https://example.com/v1?q=secret",
                                  "https://example.com/v1#fragment"])
def test_base_url_rejects_unsafe_values(monkeypatch, url):
    monkeypatch.setenv("OPENAI_BASE_URL", url)
    with pytest.raises(ConfigError):
        validated_openai_base_url()


@pytest.mark.parametrize("value", ["0", "-1", "invalid", ""])
def test_limits_fail_closed(monkeypatch, value):
    monkeypatch.setenv("GROUNDMARK_MAX_PAGES", value)
    with pytest.raises(ConfigError):
        max_pages()
