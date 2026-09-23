"""Original source names and UTC timestamps for generated artifacts."""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
import re


def source_stem(filename: str) -> str:
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    stem = Path(name).stem
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "_", stem).strip().rstrip(". ")
    stem = stem[:120].rstrip(". ") or "document"
    if re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³]", stem.split(".")[0], re.I):
        stem = "_" + stem
    return stem[:120]


def artifact_name(basename: str, suffix: str) -> str:
    if not basename or basename in {".", ".."} or re.search(r'[<>:"/\\|?*\x00-\x1f\x7f]', basename):
        raise ValueError("Invalid output basename")
    return basename + suffix


def figure_name(page: int, index: int, basename: str | None = None) -> str:
    suffix = f"page_{page:03d}_figure_{index:03d}.png"
    return artifact_name(basename, "_" + suffix) if basename else suffix


def _occupied(directory: Path, basename: str) -> bool:
    basename = basename.casefold()
    for folder in (directory, directory / "annotated", directory / "images"):
        if folder.is_dir():
            for path in folder.iterdir():
                name = path.name.casefold()
                if (name == basename or name.startswith(basename + ".")
                        or name.startswith(basename + "_page_")):
                    return True
    return False


@contextmanager
def reserve_basename(filename: str, started_at: datetime, directory: str | Path):
    """Reserve one output family across concurrent writers; retain no lock on success."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    instant = started_at.astimezone(UTC)
    stem = source_stem(filename)
    attempt = 0
    while True:
        stamp = (instant.strftime("%Y%m%d_%H%M%SZ") if attempt == 0 else
                 (instant + timedelta(microseconds=attempt - 1)).strftime("%Y%m%d_%H%M%S_%fZ"))
        basename = f"{stem}_{stamp}"
        lock = directory / f".groundmark-{basename}.lock"
        try:
            lock.mkdir()
        except FileExistsError:
            attempt += 1
            continue
        try:
            if not _occupied(directory, basename):
                yield basename
                return
        finally:
            lock.rmdir()
        attempt += 1
