"""Utilities for parsing 12306 station metadata."""

from __future__ import annotations

from dataclasses import dataclass

import requests

STATION_JS_URL = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js"


@dataclass(frozen=True)
class StationRecord:
    """A single station row from `station_name.js`."""

    name: str
    telecode: str


def parse_station_names(raw: str) -> dict[str, StationRecord]:
    """Parse `station_name.js` into a telecode keyed mapping.

    Args:
        raw: Raw JavaScript text returned by the 12306 station metadata file.

    Returns:
        A mapping keyed by station telecode.

    Raises:
        ValueError: If no `station_names` payload can be found.
    """

    marker = "station_names ='"
    start = raw.find(marker)
    if start == -1:
        raise ValueError("station_names payload not found")

    payload = raw[start + len(marker) :]
    end = payload.find("';")
    if end == -1:
        raise ValueError("station_names payload is not terminated")

    station_blob = payload[:end]
    records: dict[str, StationRecord] = {}
    for chunk in station_blob.split("@"):
        if not chunk:
            continue
        fields = chunk.split("|")
        if len(fields) < 3:
            continue
        name = fields[1].strip()
        telecode = fields[2].strip()
        if not name or not telecode:
            continue
        records[telecode] = StationRecord(name=name, telecode=telecode)
    return records


def fetch_station_map(
    session: requests.Session,
    *,
    timeout_seconds: int,
) -> dict[str, StationRecord]:
    """Download and parse the current station metadata file."""

    response = session.get(STATION_JS_URL, timeout=timeout_seconds)
    response.raise_for_status()
    return parse_station_names(response.text)


def build_station_name_index(records: dict[str, StationRecord]) -> dict[str, str]:
    """Build a station-name to telecode lookup table."""

    index: dict[str, str] = {}
    for telecode, record in records.items():
        index.setdefault(record.name, telecode)
    return index
