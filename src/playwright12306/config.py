"""Shared configuration for the 12306 fetcher."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    """Filesystem locations used by the application."""

    root: Path
    artifacts: Path
    raw: Path
    normalized: Path
    state: Path
    train_info_raw: Path
    left_ticket_raw: Path
    get_train_name_raw: Path
    trains_csv: Path
    trains_jsonl: Path
    stops_csv: Path
    routes_csv: Path
    train_info_done: Path
    left_ticket_done: Path
    error_log: Path

    @classmethod
    def from_root(cls, root: Path, artifacts_dir: Path | None = None) -> "AppPaths":
        """Build the standard directory layout for the application.

        Args:
            root: Project root directory.
            artifacts_dir: Optional custom artifacts directory.

        Returns:
            The resolved path bundle.
        """

        resolved_root = root.resolve()
        artifacts = (artifacts_dir or resolved_root / "artifacts").resolve()
        raw = artifacts / "raw"
        normalized = artifacts / "normalized"
        state = artifacts / "state"
        return cls(
            root=resolved_root,
            artifacts=artifacts,
            raw=raw,
            normalized=normalized,
            state=state,
            train_info_raw=raw / "query_train_info",
            left_ticket_raw=raw / "left_ticket",
            get_train_name_raw=raw / "get_train_name.jsonl",
            trains_csv=normalized / "trains.csv",
            trains_jsonl=normalized / "trains.jsonl",
            stops_csv=normalized / "stops.csv",
            routes_csv=normalized / "routes.csv",
            train_info_done=state / "train_info_done.txt",
            left_ticket_done=state / "left_ticket_done.txt",
            error_log=state / "errors.jsonl",
        )


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration for one fetch job."""

    query_date: str
    paths: AppPaths
    dry_run: bool = False
    force: bool = False
    timeout_seconds: int = 20
    limit_trains: int | None = None


def validate_query_date(query_date: str) -> str:
    """Validate the query date format.

    Args:
        query_date: Date string in `YYYY-MM-DD` format.

    Returns:
        The original validated date string.

    Raises:
        ValueError: If the date format is invalid.
    """

    try:
        datetime.strptime(query_date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("query_date must be in YYYY-MM-DD format") from exc
    return query_date
