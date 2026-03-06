"""Parsers for `queryTrainInfo/query` responses."""

from __future__ import annotations

from dataclasses import dataclass

import requests

from playwright12306.http_client import request_json

QUERY_TRAIN_INFO_INIT_URL = "https://kyfw.12306.cn/otn/queryTrainInfo/init"
QUERY_TRAIN_INFO_URL = "https://kyfw.12306.cn/otn/queryTrainInfo/query"


@dataclass(frozen=True)
class TrainStop:
    """A stop row in a train schedule."""

    query_date: str
    train_no: str
    station_train_code: str
    station_no: str
    station_name: str
    arrive_time: str
    start_time: str
    running_time: str
    arrive_day_diff: str
    is_start: str
    is_end: str


@dataclass(frozen=True)
class TrainSummary:
    """High level schedule summary for one train."""

    query_date: str
    train_no: str
    station_train_code: str
    train_class_name: str
    start_station_name: str
    end_station_name: str
    depart_time: str
    arrive_time: str
    duration: str
    arrive_day_diff: str


@dataclass(frozen=True)
class TrainInfoResult:
    """Parsed schedule payload with summary and stop list."""

    summary: TrainSummary
    stops: list[TrainStop]


def parse_train_info(payload: dict, query_date: str, train_no: str) -> TrainInfoResult:
    """Parse a train schedule payload.

    Args:
        payload: JSON payload returned by `queryTrainInfo/query`.
        query_date: Query date in `YYYY-MM-DD` format.
        train_no: Internal 12306 train number.

    Returns:
        Parsed schedule summary and stops.

    Raises:
        ValueError: If the payload does not include stop data.
    """

    rows = payload.get("data", {}).get("data", [])
    if not rows:
        raise ValueError("train schedule rows are empty")

    first = rows[0]
    last = rows[-1]
    station_train_code = str(first.get("station_train_code", "")).strip()
    summary = TrainSummary(
        query_date=query_date,
        train_no=train_no,
        station_train_code=station_train_code,
        train_class_name=str(first.get("train_class_name", "")).strip(),
        start_station_name=str(first.get("start_station_name", "")).strip(),
        end_station_name=str(first.get("end_station_name", "")).strip(),
        depart_time=str(first.get("start_time", "")).strip(),
        arrive_time=str(last.get("arrive_time", "")).strip(),
        duration=str(last.get("running_time", "")).strip(),
        arrive_day_diff=str(last.get("arrive_day_diff", "")).strip(),
    )

    stops: list[TrainStop] = []
    for index, row in enumerate(rows):
        raw_is_start = str(row.get("is_start", "")).strip()
        raw_is_end = str(row.get("is_end", "")).strip()
        is_start = raw_is_start or ("Y" if index == 0 else "")
        is_end = raw_is_end or ("Y" if index == len(rows) - 1 else "")
        stops.append(
            TrainStop(
                query_date=query_date,
                train_no=train_no,
                station_train_code=str(row.get("station_train_code", "")).strip(),
                station_no=str(row.get("station_no", "")).strip(),
                station_name=str(row.get("station_name", "")).strip(),
                arrive_time=str(row.get("arrive_time", "")).strip(),
                start_time=str(row.get("start_time", "")).strip(),
                running_time=str(row.get("running_time", "")).strip(),
                arrive_day_diff=str(row.get("arrive_day_diff", "")).strip(),
                is_start=is_start,
                is_end=is_end,
            )
        )
    return TrainInfoResult(summary=summary, stops=stops)


def fetch_train_info_payload(
    session: requests.Session,
    query_date: str,
    train_no: str,
    *,
    timeout_seconds: int,
) -> dict:
    """Fetch one train schedule payload."""

    return request_json(
        session,
        QUERY_TRAIN_INFO_URL,
        params={
            "leftTicketDTO.train_no": train_no,
            "leftTicketDTO.train_date": query_date,
            "rand_code": "",
        },
        referer=QUERY_TRAIN_INFO_INIT_URL,
        timeout_seconds=timeout_seconds,
    )
