"""Parsers for daily nationwide train seed data."""

from __future__ import annotations

from dataclasses import dataclass

import requests

from playwright12306.http_client import request_json

QUERY_TRAIN_INFO_INIT_URL = "https://kyfw.12306.cn/otn/queryTrainInfo/init"
QUERY_TRAIN_NAME_URL = "https://kyfw.12306.cn/otn/queryTrainInfo/getTrainName"


@dataclass(frozen=True)
class TrainSeed:
    """A single train returned by `queryTrainInfo/getTrainName`."""

    query_date: str
    station_train_code: str
    train_no: str


def parse_train_seed(payload: dict, query_date: str) -> list[TrainSeed]:
    """Parse the daily train seed response.

    Args:
        payload: JSON payload returned by `queryTrainInfo/getTrainName`.
        query_date: Query date in `YYYY-MM-DD` format.

    Returns:
        Parsed train seeds.
    """

    rows: list[TrainSeed] = []
    seen: set[tuple[str, str]] = set()
    for item in payload.get("data", []):
        station_train_code = str(item.get("station_train_code", "")).strip()
        train_no = str(item.get("train_no", "")).strip()
        if not station_train_code or not train_no:
            continue
        dedupe_key = (train_no, station_train_code)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        rows.append(
            TrainSeed(
                query_date=query_date,
                station_train_code=station_train_code,
                train_no=train_no,
            )
        )
    return rows


def fetch_train_seed_payload(
    session: requests.Session,
    query_date: str,
    *,
    timeout_seconds: int,
) -> dict:
    """Fetch the daily nationwide train seed payload."""

    return request_json(
        session,
        QUERY_TRAIN_NAME_URL,
        params={"date": query_date},
        referer=QUERY_TRAIN_INFO_INIT_URL,
        timeout_seconds=timeout_seconds,
    )
