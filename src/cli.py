"""Launch the UI or extract a document using the installed application."""

import argparse
from contextlib import redirect_stdout
from importlib.metadata import version
import os
from pathlib import Path
import subprocess
import sys

from dotenv import load_dotenv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract a file, or launch the web UI when no file is given.", prog="groundmark")
    parser.add_argument("file", nargs="?", type=Path, help="Source PDF or image")
    parser.add_argument("output_dir", nargs="?", type=Path, help="Destination for selected outputs")
    parser.add_argument("--version", action="version", version=f"GroundMark {version('groundmark')}")
    parser.add_argument("--env-file", type=Path, help="Configuration file (default: workspace .env)")
    parser.add_argument("--workspace", type=Path,
                        help="Folder for .env and data/ outputs (default: current folder)")
    parser.add_argument("--port", type=int, help="UI server port (default: 5805)")
    parser.add_argument("--host", help="UI bind address (default: 127.0.0.1)")
    parser.add_argument("--headless", action="store_true", help="Do not open a browser")
    from src.export import FORMATS
    for name in sorted(FORMATS):
        parser.add_argument(f"--{name}", action="store_true", help=f"Write {name} output")
    parser.add_argument("--all", action="store_true", help="Write every output format")
    parser.add_argument("--start-page", type=int, help="First page, inclusive (default: 1)")
    parser.add_argument("--end-page", type=int, help="Last page, inclusive (default: last)")
    parser.add_argument("--view", choices=["full", "clean"], help="Rendering view (default: full)")
    parser.add_argument("--detailed-layout", action="store_true", help="Experimental structure extraction")
    parser.add_argument("--overwrite", action="store_true", help="Allow writing generated files in a nonempty destination")
    args = parser.parse_args(argv)
    if (args.file is None) != (args.output_dir is None):
        parser.error("provide both a file and an output directory")
    if args.port is not None and not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    formats = {name for name in FORMATS if getattr(args, name.replace("-", "_"))}
    if args.file and (args.workspace is not None or args.port is not None or args.host is not None or args.headless):
        parser.error("--workspace, --port, --host and --headless apply only to the UI")
    if not args.file and (formats or args.all or args.start_page is not None or args.end_page is not None
                          or args.view or args.detailed_layout or args.overwrite):
        parser.error("extraction options require a file and output directory")
    workspace = (args.workspace or Path.cwd()).expanduser().resolve()
    env_file = args.env_file.expanduser().resolve() if args.env_file else workspace / ".env"
    if args.env_file and not env_file.is_file():
        parser.error("--env-file must name an existing file")
    load_dotenv(env_file, override=False)
    # Stop implicit dotenv discovery in subsequently imported model clients.
    os.environ["GROUNDMARK_ENV_LOADED"] = "1"
    if args.file:
        try:
            return _extract(args, parser, set(FORMATS) if args.all else formats or {"markdown"})
        except OSError as exc:
            print(f"Cannot access input or output ({type(exc).__name__})", file=sys.stderr)
            return 1
    workspace.mkdir(parents=True, exist_ok=True)
    app = Path(__file__).resolve().parent / "ui" / "app.py"
    command = [sys.executable, "-m", "streamlit", "run", str(app),
               f"--server.port={args.port or 5805}", f"--server.address={args.host or '127.0.0.1'}",
               f"--server.headless={str(args.headless).lower()}"]
    try:
        return subprocess.call(command, cwd=workspace)
    except KeyboardInterrupt:
        return 130


def _extract(args, parser, formats: set[str]) -> int:
    from src.preprocess import count_pages

    source = args.file.expanduser().resolve()
    destination = args.output_dir.expanduser().resolve()
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        parser.error("OPENAI_API_KEY is required; set it in the environment or --env-file")
    try:
        pages = count_pages(source)
    except Exception:
        parser.error("input must be a readable supported PDF or image")
    start = args.start_page if args.start_page is not None else 1
    end = args.end_page if args.end_page is not None else pages
    if not 1 <= start <= end <= pages:
        parser.error(f"page range must be within 1..{pages}")
    if destination.exists() and not destination.is_dir():
        parser.error("output directory is an existing file")
    if destination in source.parents:
        parser.error("input must be outside the output directory to prevent overwriting it")
    if destination.exists() and any(destination.iterdir()) and not args.overwrite:
        parser.error("output directory is not empty; choose another or pass --overwrite")
    try:
        destination.mkdir(parents=True, exist_ok=True)
        from src.graph import run_graph
        with redirect_stdout(sys.stderr):
            result = run_graph(str(source), start_page=start, end_page=end,
                               output_dir=destination, formats=formats, view=args.view or "full",
                               detailed_layout=args.detailed_layout,
                               on_progress=lambda event: print(
                                   f"Pages: {event['completed']}/{event['total']}", file=sys.stderr))
        for path in result.get("output_paths", []):
            print(path)
        for message in [result.get("parse_error"), *result.get("export_errors", []),
                        *result.get("figure_warnings", [])]:
            if message:
                print(message, file=sys.stderr)
        print(f"Status: {result['status']}", file=sys.stderr)
        if result["status"] == "parse_failed":
            return 1
        return 3 if (result["status"] == "parsed_partial" or result.get("export_errors")
                     or result.get("figure_warnings")) else 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"Extraction failed ({type(exc).__name__})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
