"""Check the exact release manifest and source/prompt bytes against the checkout."""

from __future__ import annotations

import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULES = (
    "__init__ annotate chat cli config diagnostics export figures graph layout llm "
    "markdown models output_names parse preprocess prompts usage ui/__init__ ui/app ui/clipboard"
).split()
PROMPTS = ("chat-answer", "chat-verify", "parse-page-structured", "parse-page")


def _manifest(*, wheel: bool) -> dict[str, Path | None]:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    files = {f"src/{module}.py": ROOT / "src" / f"{module}.py" for module in MODULES}
    prompt_dir = "src/_runtime_prompts" if wheel else "prompts/runtime"
    files.update({f"{prompt_dir}/{name}.md": ROOT / "prompts/runtime" / f"{name}.md" for name in PROMPTS})
    if wheel:
        prefix = f"groundmark-{version}.dist-info"
        files.update({f"{prefix}/{name}": None for name in ("METADATA", "WHEEL", "entry_points.txt", "RECORD")})
        files[f"{prefix}/licenses/LICENSE"] = ROOT / "LICENSE"
        return files
    files.update({name: ROOT / name for name in (".gitignore", "LICENSE", "README.md", "pyproject.toml")})
    files["PKG-INFO"] = None
    return {f"groundmark-{version}/{name}": path for name, path in files.items()}


def _check(names: list[str], *, wheel: bool) -> dict[str, Path | None]:
    expected = _manifest(wheel=wheel)
    if len(names) != len(set(names)):
        raise SystemExit("release archive contains duplicate members")
    missing, unexpected = set(expected) - set(names), set(names) - set(expected)
    if missing or unexpected:
        raise SystemExit(f"release manifest mismatch: missing={sorted(missing)}, unexpected={sorted(unexpected)}")
    return expected


def _check_bytes(name: str, data: bytes, source: Path | None) -> None:
    if source is not None and data != source.read_bytes():
        raise SystemExit(f"release content differs from checkout: {name}")


def main(directory: str = "dist") -> None:
    dist = Path(directory)
    wheels = list(dist.glob("*.whl"))
    sdists = list(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit("expected exactly one wheel and one source archive")
    with zipfile.ZipFile(wheels[0]) as archive:
        for name, source in _check(archive.namelist(), wheel=True).items():
            _check_bytes(name, archive.read(name), source)
    with tarfile.open(sdists[0], "r:gz") as archive:
        manifest = _check(archive.getnames(), wheel=False)
        for member in archive.getmembers():
            if not member.isfile():
                raise SystemExit("source archive contains a non-regular file")
            with archive.extractfile(member) as handle:
                _check_bytes(member.name, handle.read(), manifest[member.name])
    print("release artifacts verified (exact manifest and checkout content)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dist")
