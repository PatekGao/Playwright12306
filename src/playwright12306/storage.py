"""Filesystem storage helpers for raw and normalized outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from playwright12306.models import to_serializable_dict


def append_jsonl(path: Path, row: Any) -> None:
    """Append one JSON line to a target file.

    Args:
        path: Destination JSONL file.
        row: Mapping or dataclass-like payload.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = to_serializable_dict(row)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_json(path: Path, row: Any) -> None:
    """Write a JSON document."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(row, list):
        payload = row
    elif isinstance(row, dict):
        payload = row
    else:
        payload = to_serializable_dict(row)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def read_json(path: Path) -> Any:
    """Read a JSON document from disk."""

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    """Write a collection of dict rows into a CSV file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(list(rows))
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_jsonl(path: Path, rows: Iterable[Any]) -> None:
    """Write a full JSONL file in one pass."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = to_serializable_dict(row) if not isinstance(row, dict) else row
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_done_keys(path: Path) -> set[str]:
    """Load line-delimited state keys from disk."""

    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def append_done_key(path: Path, key: str) -> None:
    """Append one completion marker to a state file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{key}\n")
