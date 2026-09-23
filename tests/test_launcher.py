"""Windows launcher delegates environment setup and arguments to uv."""

from pathlib import Path
import os
import subprocess

import pytest


@pytest.mark.skipif(os.name != "nt", reason="Windows launcher")
@pytest.mark.parametrize("exit_code", [0, 7])
def test_launcher_forwards_arguments_and_exit_status(tmp_path, exit_code):
    launcher = Path(__file__).parents[1] / "run.cmd"
    (tmp_path / "run.cmd").write_bytes(launcher.read_bytes())
    (tmp_path / "uv.cmd").write_text(
        '@echo off\necho %*>>calls.txt\n'
        f'exit /b {exit_code}\n'
    )
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", "run.cmd --port 5806 --headless"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == exit_code
    assert (tmp_path / "calls.txt").read_text().strip() == "run groundmark --port 5806 --headless"
