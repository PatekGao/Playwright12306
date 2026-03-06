"""CLI entry point for fetching nationwide 12306 train data."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from playwright12306.config import AppConfig, AppPaths, validate_query_date
from playwright12306.pipeline import NationwideTrainPipeline


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""

    parser = argparse.ArgumentParser(
        description="Fetch nationwide 12306 train schedules and prices."
    )
    parser.add_argument("--query-date", required=True, help="Date in YYYY-MM-DD format.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the execution plan without sending network requests.",
    )
    parser.add_argument(
        "--limit-trains",
        type=int,
        default=None,
        help="Fetch only the first N train seeds, useful for quick verification.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a shell-friendly exit code."""

    args = build_parser().parse_args(argv)
    query_date = validate_query_date(args.query_date)
    paths = AppPaths.from_root(PROJECT_ROOT)
    if args.dry_run:
        print(f"[dry-run] query_date={query_date}")
        print(f"[dry-run] artifacts_dir={paths.artifacts}")
        print(f"[dry-run] limit_trains={args.limit_trains}")
        return 0
    config = AppConfig(
        query_date=query_date,
        paths=paths,
        dry_run=False,
        limit_trains=args.limit_trains,
    )
    result = NationwideTrainPipeline(config).run()
    print(f"trains={result.train_count} stops={result.stop_count} routes={result.route_count}")
    print(result.trains_csv)
    print(result.stops_csv)
    print(result.routes_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
