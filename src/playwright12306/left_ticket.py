"""Parsers for `leftTicket/queryG` result rows."""

from __future__ import annotations

from dataclasses import dataclass

import requests

from playwright12306.http_client import request_json

LEFT_TICKET_INIT_URL = "https://kyfw.12306.cn/otn/leftTicket/init?linktypeid=dc"
LEFT_TICKET_QUERY_URL = "https://kyfw.12306.cn/otn/leftTicket/queryG"


@dataclass(frozen=True)
class LeftTicketRow:
    """A parsed `leftTicket/queryG` row."""

    raw_row: str
    train_no: str
    station_train_code: str
    from_station_code: str
    to_station_code: str
    start_station_code: str
    end_station_code: str
    depart_time: str
    arrive_time: str
    duration: str
    can_web_buy: str
    yp_info_new: str
    seat_types: str
    sale_status: str = ""


def parse_left_ticket_row(row: str) -> LeftTicketRow:
    """Parse a pipe-delimited `leftTicket/queryG` row.

    Args:
        row: One item from the `data.result` list.

    Returns:
        Parsed row fields needed by the pipeline.

    Raises:
        ValueError: If the row is too short to parse.
    """

    parts = row.split("|")
    if len(parts) < 40:
        raise ValueError("left ticket row is shorter than expected")

    return LeftTicketRow(
        raw_row=row,
        train_no=parts[2].strip(),
        station_train_code=parts[3].strip(),
        start_station_code=parts[4].strip(),
        end_station_code=parts[5].strip(),
        from_station_code=parts[6].strip(),
        to_station_code=parts[7].strip(),
        depart_time=parts[8].strip(),
        arrive_time=parts[9].strip(),
        duration=parts[10].strip(),
        can_web_buy=parts[11].strip(),
        yp_info_new=parts[39].strip(),
        seat_types=parts[35].strip(),
        sale_status=parts[1].strip(),
    )


def parse_left_ticket_payload(payload: dict) -> tuple[list[LeftTicketRow], dict[str, str]]:
    """Parse a full `leftTicket/queryG` payload."""

    data = payload.get("data", {})
    rows = [parse_left_ticket_row(item) for item in data.get("result", []) if item]
    station_map = data.get("map", {}) or {}
    return rows, station_map


def bootstrap_left_ticket_session(
    session: requests.Session,
    *,
    timeout_seconds: int,
) -> None:
    """Initialize cookies required by the left ticket endpoints."""

    response = session.get(LEFT_TICKET_INIT_URL, timeout=timeout_seconds)
    response.raise_for_status()


def fetch_left_ticket_payload(
    session: requests.Session,
    query_date: str,
    from_station_code: str,
    to_station_code: str,
    *,
    timeout_seconds: int,
) -> dict:
    """Fetch a left ticket payload for one route."""

    return request_json(
        session,
        LEFT_TICKET_QUERY_URL,
        params={
            "leftTicketDTO.train_date": query_date,
            "leftTicketDTO.from_station": from_station_code,
            "leftTicketDTO.to_station": to_station_code,
            "purpose_codes": "ADULT",
        },
        referer=LEFT_TICKET_INIT_URL,
        timeout_seconds=timeout_seconds,
    )
