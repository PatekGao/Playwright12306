import subprocess
import sys
from pathlib import Path

from scripts.fetch_national_trains import build_parser, main


def test_build_parser_accepts_query_date() -> None:
    parser = build_parser()
    args = parser.parse_args(["--query-date", "2026-03-20"])
    assert args.query_date == "2026-03-20"


def test_build_parser_accepts_dry_run() -> None:
    parser = build_parser()
    args = parser.parse_args(["--query-date", "2026-03-20", "--dry-run"])
    assert args.dry_run is True


def test_main_returns_zero_for_dry_run() -> None:
    assert main(["--query-date", "2026-03-20", "--dry-run"]) == 0


def test_build_parser_accepts_limit_trains() -> None:
    parser = build_parser()
    args = parser.parse_args(["--query-date", "2026-03-20", "--limit-trains", "5"])
    assert args.limit_trains == 5


def test_script_invocation_succeeds_for_dry_run() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "fetch_national_trains.py"
    result = subprocess.run(
        [sys.executable, str(script), "--query-date", "2026-03-20", "--dry-run"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
