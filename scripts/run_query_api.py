"""Run the local FastAPI search server."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from playwright12306.search_api import create_app


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the API server."""

    parser = argparse.ArgumentParser(description="Run the local 12306 search API.")
    parser.add_argument("--db-path", default="data/train_search.db", help="SQLite database path.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    parser.add_argument("--port", type=int, default=8000, help="Bind port.")
    parser.add_argument(
        "--web-dist",
        default="web/dist",
        help="Built frontend directory to mount when present.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the FastAPI server."""

    args = build_parser().parse_args(argv)
    app = create_app(
        Path(args.db_path).expanduser(),
        web_dist=Path(args.web_dist).expanduser(),
    )
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
