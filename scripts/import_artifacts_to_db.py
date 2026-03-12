"""Import normalized artifacts into the local SQLite search database."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from playwright12306.search_importer import import_artifacts


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the import script."""

    parser = argparse.ArgumentParser(description="Import train artifacts into SQLite.")
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts/2026-03-18",
        help="Artifacts directory that contains normalized/*.csv.",
    )
    parser.add_argument(
        "--db-path",
        default="data/train_search.db",
        help="Target SQLite database path.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the import command."""

    args = build_parser().parse_args(argv)
    result = import_artifacts(
        artifacts_dir=Path(args.artifacts_dir).expanduser(),
        db_path=Path(args.db_path).expanduser(),
    )
    print(f"query_date={result.query_date}")
    print(f"trains={result.train_count} stops={result.stop_count} routes={result.route_count}")
    print(f"seat_prices={result.seat_price_count}")
    print(result.db_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
