"""Shared lightweight models used by the fetch pipeline."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def to_serializable_dict(value: Any) -> dict[str, Any]:
    """Convert a dataclass-like object into a JSON-serializable dict."""

    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return value
    raise TypeError(f"unsupported value type: {type(value)!r}")
