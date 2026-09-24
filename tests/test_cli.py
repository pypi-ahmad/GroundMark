"""Launcher keeps installed code separate from writable user data."""

from pathlib import Path
import sys

import pytest

from src import cli


def test_launcher_uses_workspace_and_installed_app(tmp_path, monkeypatch):
    workspace = tmp_path / "user workspace"
    workspace.mkdir()
    (workspace / ".env").write_text("GROUNDMARK_TEST_SETTING=loaded\n")
    monkeypatch.delenv("GROUNDMARK_TEST_SETTING", raising=False)
    calls = []
    monkeypatch.setattr(cli.subprocess, "call", lambda command, **kw: calls.append((command, kw)) or 7)
    assert cli.main(["--workspace", str(workspace), "--port", "5806", "--headless"]) == 7
    command, kwargs = calls[0]
    assert command[:4] == [sys.executable, "-m", "streamlit", "run"]
    assert Path(command[4]).is_file()
    assert "--server.port=5806" in command
    assert "--server.address=127.0.0.1" in command
    assert "--server.allowedHosts=127.0.0.1" in command
    assert "--server.allowedHosts=localhost" in command
    assert "--server.allowedHosts=::1" in command
    assert "--server.enableCORS=true" in command
    assert "--server.enableXsrfProtection=true" in command
    assert "--server.headless=true" in command
    assert kwargs["cwd"] == workspace.resolve()
    import os
    assert os.environ["GROUNDMARK_TEST_SETTING"] == "loaded"
    monkeypatch.delenv("GROUNDMARK_TEST_SETTING")


@pytest.mark.parametrize("port", ["0", "65536"])
def test_invalid_port_does_not_create_workspace(port, tmp_path):
    workspace = tmp_path / "not-created"
    with pytest.raises(SystemExit, match="2"):
        cli.main(["--port", port, "--workspace", str(workspace)])
    assert not workspace.exists()
