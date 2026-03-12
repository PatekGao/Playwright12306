"""Realtime 12306 ticket query service, task management, and helpers."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
import csv
import io
import json
from pathlib import Path
import threading
import time
from typing import Any, Callable, Iterable
import uuid

from playwright12306.http_client import create_session
from playwright12306.left_ticket import (
    LeftTicketRow,
    bootstrap_left_ticket_session,
    fetch_left_ticket_payload,
    parse_left_ticket_payload,
)
from playwright12306.price_parser import SEAT_NAME_MAP, parse_info_all_list
from playwright12306.stations import StationRecord, build_station_name_index, fetch_station_map
from playwright12306.train_info import fetch_train_info_payload, parse_train_info
from playwright12306.train_seed import fetch_train_seed_payload, parse_train_seed


MAX_REALTIME_DAYS = 7
DEFAULT_ROUTE_DAY_WORKERS = 2
DEFAULT_TRAIN_INFO_WORKERS = 4
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_JOB_TTL_SECONDS = 30 * 60
FINAL_JOB_STATUSES = {"completed", "failed"}

TRAIN_CLASS_NAME_MAP = {
    "G": "高速",
    "C": "城际",
    "D": "动车",
    "Z": "直达",
    "T": "特快",
    "K": "快速",
    "Y": "旅游",
    "S": "市域",
}


def normalize_train_class_filter(value: str) -> str:
    """Normalize a user-provided train class filter."""

    text = value.strip()
    if "-" in text:
        _, suffix = text.split("-", 1)
        text = suffix.strip() or text
    return text


CITY_SUFFIXES = [
    "机场东",
    "机场西",
    "虹桥",
    "松江",
    "东站",
    "西站",
    "南站",
    "北站",
    "机场",
    "东",
    "西",
    "南",
    "北",
]


def normalize_city_name(name: str) -> str:
    """Normalize a station or city name to a city-level label."""

    text = name.strip()
    for suffix in CITY_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            return text[: -len(suffix)]
    return text


def build_city_name_index(station_by_code: dict[str, StationRecord]) -> dict[str, list[StationRecord]]:
    """Build a city-name to station list index from station records."""

    city_name_index: dict[str, list[StationRecord]] = {}
    for record in station_by_code.values():
        city_name_index.setdefault(normalize_city_name(record.name), []).append(record)
    return city_name_index


def choose_city_anchor_station(
    city_name: str,
    *,
    station_name_index: dict[str, str],
    city_name_index: dict[str, list[StationRecord]],
) -> StationRecord:
    """Choose one representative station for a loose city-level route query."""

    if city_name in station_name_index:
        telecode = station_name_index[city_name]
        return next(record for record in city_name_index[normalize_city_name(city_name)] if record.telecode == telecode)

    candidates = city_name_index[normalize_city_name(city_name)]
    # Prefer short, city-core station names such as "上海" over branch stations such as "上海虹桥".
    return sorted(candidates, key=lambda record: (len(record.name), record.name, record.telecode))[0]

SEAT_INVENTORY_INDEX_MAP = [
    ("6", 20),
    ("4", 23),
    ("2", 24),
    ("P", 25),
    ("W", 26),
    ("3", 28),
    ("1", 29),
    ("O", 30),
    ("M", 31),
    ("9", 32),
    ("F", 33),
]


class RealtimeQueryError(ValueError):
    """Raised when a realtime query request is invalid."""


ProgressCallback = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class RealtimeQueryRequest:
    """Normalized realtime query request."""

    date_from: str
    date_to: str
    query_mode: str
    from_station_name: str = ""
    to_station_name: str = ""
    train_code: str = ""
    train_class_name: str = ""
    query_scope: str = "station"


@dataclass
class RealtimeJob:
    """In-memory realtime job state."""

    job_id: str
    request: dict[str, Any]
    created_at: str
    updated_at: str
    status: str = "queued"
    result: dict[str, Any] | None = None
    error: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    condition: threading.Condition = field(default_factory=threading.Condition, repr=False)

    def serialize(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of the job."""

        return {
            "job_id": self.job_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "request": self.request,
            "result": self.result,
            "error": self.error,
        }


def normalize_train_class(train_code: str, raw_value: str) -> str:
    """Return a user-facing train class."""

    normalized = raw_value.strip()
    if normalized:
        return normalized
    return TRAIN_CLASS_NAME_MAP.get(train_code[:1].upper(), "其他")


def parse_duration_to_minutes(duration: str) -> int | None:
    """Convert `HH:MM` text to minutes."""

    text = duration.strip()
    if not text or ":" not in text:
        return None
    try:
        hours_text, minutes_text = text.split(":", 1)
        return int(hours_text) * 60 + int(minutes_text)
    except ValueError:
        return None


def iter_query_dates(date_from: str, date_to: str) -> list[str]:
    """Expand a closed date interval into a list of ISO dates."""

    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)
    if end < start:
        raise RealtimeQueryError("date_to must be greater than or equal to date_from")
    span = (end - start).days + 1
    if span > MAX_REALTIME_DAYS:
        raise RealtimeQueryError(f"date range cannot exceed {MAX_REALTIME_DAYS} days")
    return [(start + timedelta(days=index)).isoformat() for index in range(span)]


def normalize_realtime_request(payload: dict[str, Any]) -> RealtimeQueryRequest:
    """Validate and normalize a realtime query request payload."""

    date_from = str(payload.get("date_from") or payload.get("date") or "").strip()
    date_to = str(payload.get("date_to") or payload.get("date") or date_from).strip()
    query_mode = str(payload.get("query_mode", "")).strip()
    from_station_name = str(payload.get("from_station_name", "")).strip()
    to_station_name = str(payload.get("to_station_name", "")).strip()
    train_code = str(payload.get("train_code", "")).strip().upper()
    train_class_name = normalize_train_class_filter(str(payload.get("train_class_name", "")))
    query_scope = str(payload.get("query_scope", "station")).strip() or "station"

    if not date_from:
        raise RealtimeQueryError("date_from is required")
    iter_query_dates(date_from, date_to)

    if not query_mode:
        if from_station_name and to_station_name:
            query_mode = "route"
        elif from_station_name or to_station_name or train_code:
            query_mode = "single_head"
        else:
            raise RealtimeQueryError("provide a route, one station, or a train_code")

    if query_mode not in {"route", "single_head"}:
        raise RealtimeQueryError("query_mode must be route or single_head")
    if query_scope not in {"station", "city"}:
        raise RealtimeQueryError("query_scope must be station or city")
    if query_mode == "route":
        if not from_station_name or not to_station_name:
            raise RealtimeQueryError("route mode requires from_station_name and to_station_name")
    else:
        if from_station_name and to_station_name:
            raise RealtimeQueryError("single_head mode accepts only one station")
        if not (from_station_name or to_station_name or train_code):
            raise RealtimeQueryError("single_head mode requires one station or train_code")

    return RealtimeQueryRequest(
        date_from=date_from,
        date_to=date_to,
        query_mode=query_mode,
        from_station_name=from_station_name,
        to_station_name=to_station_name,
        train_code=train_code,
        train_class_name=train_class_name,
        query_scope=query_scope,
    )


def classify_upstream_error(error: Exception) -> str:
    """Classify one upstream exception."""

    text = str(error).lower()
    if "expected json but received html" in text or "<!doctype" in text or "<html" in text:
        return "upstream_blocked"
    if "invalid json response" in text or "rows are empty" in text:
        return "upstream_invalid"
    return "upstream_error"


def format_upstream_error_message(error: Exception) -> str:
    """Return a user-facing upstream error message."""

    error_type = classify_upstream_error(error)
    if error_type == "upstream_blocked":
        return "12306 返回了拦截页或风控页，本次实时查询被上游阻断，请稍后重试。"
    if error_type == "upstream_invalid":
        return "12306 返回了非预期数据，当前无法解析，请稍后重试。"
    return str(error)


def is_inventory_available(value: str) -> bool:
    """Return whether one seat inventory text indicates availability."""

    text = value.strip()
    if not text or text in {"--", "*", "无"}:
        return False
    return True


def filter_price_map(prices: dict[str, str]) -> dict[str, str]:
    """Keep user-facing seat codes and collapse implementation-specific variants."""

    filtered = {code: price for code, price in prices.items() if code in SEAT_NAME_MAP}
    if filtered:
        return filtered
    return prices


def build_seat_offers(row: LeftTicketRow) -> list[dict[str, Any]]:
    """Build structured seat offers for one realtime route row."""

    prices = filter_price_map(parse_info_all_list(row.yp_info_new))
    inventory_map: dict[str, str] = {}
    for seat_code, index in SEAT_INVENTORY_INDEX_MAP:
        inventory_map[seat_code] = row.part(index)

    ordered_codes: list[str] = []
    for seat_code, _ in SEAT_INVENTORY_INDEX_MAP:
        if seat_code not in ordered_codes:
            ordered_codes.append(seat_code)
    for seat_code in prices:
        if seat_code not in ordered_codes:
            ordered_codes.append(seat_code)

    offers: list[dict[str, Any]] = []
    for seat_code in ordered_codes:
        inventory_text = inventory_map.get(seat_code, "")
        price_text = prices.get(seat_code)
        if not inventory_text and price_text is None:
            continue
        offers.append(
            {
                "seat_code": seat_code,
                "seat_name": SEAT_NAME_MAP.get(seat_code, seat_code),
                "price": float(price_text) if price_text is not None else None,
                "inventory_text": inventory_text,
                "is_available": is_inventory_available(inventory_text),
            }
        )
    offers.sort(
        key=lambda item: (
            item["price"] is None,
            item["price"] if item["price"] is not None else 0,
            item["seat_name"],
        )
    )
    return offers


def compute_min_price(seat_offers: Iterable[dict[str, Any]]) -> float | None:
    """Return the minimum non-null price from a seat offer list."""

    values = [item["price"] for item in seat_offers if item.get("price") is not None]
    return min(values) if values else None


def build_daily_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Build one per-day summary."""

    available_count = 0
    cheapest: float | None = None
    fastest_minutes: int | None = None
    fastest_duration: str | None = None
    for item in items:
        min_price = item.get("min_price")
        if min_price is not None:
            cheapest = min(cheapest, min_price) if cheapest is not None else min_price
        if any(seat.get("is_available") for seat in item.get("seat_offers", [])):
            available_count += 1
        duration_minutes = parse_duration_to_minutes(str(item.get("duration", "")))
        if duration_minutes is not None and (
            fastest_minutes is None or duration_minutes < fastest_minutes
        ):
            fastest_minutes = duration_minutes
            fastest_duration = str(item.get("duration", ""))
    return {
        "matched_train_count": len(items),
        "available_train_count": available_count,
        "cheapest_available_price": cheapest,
        "fastest_duration": fastest_duration,
    }


def aggregate_results(query_mode: str, daily_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate daily results across the queried date range."""

    aggregated: dict[tuple[str, str], dict[str, Any]] = {}
    for daily in daily_results:
        for item in daily.get("items", []):
            key_suffix = (
                item.get("matched_route_signature") or item.get("route_signature", "")
                if query_mode == "route"
                else item["matched_station_name"]
            )
            key = (item["train_code"], key_suffix)
            entry = aggregated.setdefault(
                key,
                {
                    "train_code": item["train_code"],
                    "train_class_name": item["train_class_name"],
                    "start_station_name": item["start_station_name"],
                    "end_station_name": item["end_station_name"],
                    "query_mode": query_mode,
                    "query_scope": item.get("query_scope", "station"),
                    "route_signature": item.get("route_signature", ""),
                    "matched_route_signature": item.get("matched_route_signature", ""),
                    "matched_from_station_name": item.get("matched_from_station_name", ""),
                    "matched_to_station_name": item.get("matched_to_station_name", ""),
                    "matched_station_name": item.get("matched_station_name", ""),
                    "available_days": 0,
                    "sold_out_days": 0,
                    "first_seen_date": item["query_date"],
                    "last_seen_date": item["query_date"],
                    "min_price": None,
                    "max_price": None,
                    "sample_depart_time": item["depart_time"],
                    "sample_arrive_time": item["arrive_time"],
                    "sample_duration": item["duration"],
                },
            )
            entry["first_seen_date"] = min(entry["first_seen_date"], item["query_date"])
            entry["last_seen_date"] = max(entry["last_seen_date"], item["query_date"])
            min_price = item.get("min_price")
            if min_price is not None:
                entry["min_price"] = (
                    min(entry["min_price"], min_price)
                    if entry["min_price"] is not None
                    else min_price
                )
                entry["max_price"] = (
                    max(entry["max_price"], min_price)
                    if entry["max_price"] is not None
                    else min_price
                )
            if any(seat.get("is_available") for seat in item.get("seat_offers", [])):
                entry["available_days"] += 1
            elif query_mode == "route":
                entry["sold_out_days"] += 1
    return sorted(
        aggregated.values(),
        key=lambda item: (
            item["min_price"] is None,
            item["min_price"] if item["min_price"] is not None else 0,
            item["sample_duration"],
            item["train_code"],
        ),
    )


def build_overall_summary(
    *,
    daily_results: list[dict[str, Any]],
    aggregated_results: list[dict[str, Any]],
    partial_failures: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a top-level query summary."""

    cheapest: float | None = None
    fastest_minutes: int | None = None
    fastest_duration: str | None = None
    for daily in daily_results:
        candidate_price = daily["summary"].get("cheapest_available_price")
        if candidate_price is not None:
            cheapest = min(cheapest, candidate_price) if cheapest is not None else candidate_price
        candidate_duration = daily["summary"].get("fastest_duration")
        duration_minutes = parse_duration_to_minutes(candidate_duration or "")
        if duration_minutes is not None and (
            fastest_minutes is None or duration_minutes < fastest_minutes
        ):
            fastest_minutes = duration_minutes
            fastest_duration = candidate_duration
    available_train_count = sum(1 for item in aggregated_results if item["available_days"] > 0)
    return {
        "total_days": len(daily_results) + len(partial_failures),
        "successful_days": len(daily_results),
        "failed_days": len(partial_failures),
        "available_train_count": available_train_count,
        "cheapest_available_price": cheapest,
        "fastest_duration": fastest_duration,
        "matched_train_count": len(aggregated_results),
    }


class RealtimeQueryService:
    """Shared realtime query service for CLI and FastAPI."""

    def __init__(
        self,
        *,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        route_day_workers: int = DEFAULT_ROUTE_DAY_WORKERS,
        train_info_workers: int = DEFAULT_TRAIN_INFO_WORKERS,
        station_fetcher: Callable[[Any], dict[str, StationRecord]] | None = None,
        train_seed_fetcher: Callable[[Any, str], dict[str, Any]] | None = None,
        train_info_fetcher: Callable[[Any, str, str], dict[str, Any]] | None = None,
        left_ticket_bootstrapper: Callable[[Any], None] | None = None,
        left_ticket_fetcher: Callable[[Any, str, str, str], dict[str, Any]] | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.route_day_workers = route_day_workers
        self.train_info_workers = train_info_workers
        self._station_fetcher = station_fetcher or (
            lambda session: fetch_station_map(session, timeout_seconds=self.timeout_seconds)
        )
        self._train_seed_fetcher = train_seed_fetcher or (
            lambda session, query_date: fetch_train_seed_payload(
                session, query_date, timeout_seconds=self.timeout_seconds
            )
        )
        self._train_info_fetcher = train_info_fetcher or (
            lambda session, query_date, train_no: fetch_train_info_payload(
                session, query_date, train_no, timeout_seconds=self.timeout_seconds
            )
        )
        self._left_ticket_bootstrapper = left_ticket_bootstrapper or (
            lambda session: bootstrap_left_ticket_session(
                session, timeout_seconds=self.timeout_seconds
            )
        )
        self._left_ticket_fetcher = left_ticket_fetcher or (
            lambda session, query_date, from_code, to_code: fetch_left_ticket_payload(
                session,
                query_date,
                from_code,
                to_code,
                timeout_seconds=self.timeout_seconds,
            )
        )
        self._station_cache_lock = threading.Lock()
        self._station_by_code: dict[str, StationRecord] | None = None
        self._station_name_index: dict[str, str] | None = None
        self._city_name_index: dict[str, list[StationRecord]] | None = None

    def list_station_names(self) -> list[str]:
        """Return the cached station name list."""

        _, station_name_index, _ = self._get_station_indexes()
        return sorted(station_name_index.keys())

    def list_city_names(self) -> list[str]:
        """Return the cached city name list."""

        _, _, city_name_index = self._get_station_indexes()
        return sorted(city_name_index.keys())

    def get_train_detail(
        self,
        *,
        query_date: str,
        train_no: str,
        from_station_name: str = "",
        to_station_name: str = "",
    ) -> dict[str, Any]:
        """Fetch one realtime train detail payload."""

        station_by_code, station_name_index, _ = self._get_station_indexes()
        session = create_session()
        payload = self._train_info_fetcher(session, query_date, train_no)
        train_info = parse_train_info(payload, query_date, train_no)
        summary = train_info.summary
        detail = {
            "train": {
                "query_date": query_date,
                "train_no": summary.train_no,
                "train_code": summary.station_train_code,
                "train_class_name": normalize_train_class(
                    summary.station_train_code, summary.train_class_name
                ),
                "start_station_name": summary.start_station_name,
                "end_station_name": summary.end_station_name,
                "depart_time": summary.depart_time,
                "arrive_time": summary.arrive_time,
                "duration": summary.duration,
                "arrive_day_diff": summary.arrive_day_diff,
            },
            "stops": [
                {
                    "query_date": stop.query_date,
                    "train_no": stop.train_no,
                    "station_train_code": stop.station_train_code,
                    "station_no": stop.station_no,
                    "station_name": stop.station_name,
                    "arrive_time": stop.arrive_time,
                    "start_time": stop.start_time,
                    "running_time": stop.running_time,
                    "arrive_day_diff": stop.arrive_day_diff,
                    "is_start": stop.is_start,
                    "is_end": stop.is_end,
                }
                for stop in train_info.stops
            ],
            "seat_offers": [],
            "route_signature": "",
        }
        if from_station_name and to_station_name:
            from_code = station_name_index.get(from_station_name)
            to_code = station_name_index.get(to_station_name)
            if from_code and to_code:
                route_payload = self._request_with_retry(
                    lambda session_arg: (
                        self._left_ticket_bootstrapper(session_arg),
                        self._left_ticket_fetcher(session_arg, query_date, from_code, to_code),
                    )[1]
                )
                rows, _ = parse_left_ticket_payload(route_payload)
                matched_row = next((row for row in rows if row.train_no == train_no), None)
                if matched_row:
                    detail["seat_offers"] = build_seat_offers(matched_row)
                    detail["route_signature"] = f"{from_code}->{to_code}"
                    detail["train"]["from_station_name"] = from_station_name
                    detail["train"]["to_station_name"] = to_station_name
                    detail["train"]["sale_status"] = matched_row.sale_status
                    detail["train"]["can_web_buy"] = matched_row.can_web_buy
        return detail

    def run_query(
        self,
        request: RealtimeQueryRequest,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """Run one realtime query and return a JSON-serializable result."""

        query_dates = iter_query_dates(request.date_from, request.date_to)
        station_by_code, station_name_index, city_name_index = self._get_station_indexes()
        self._emit(
            progress_callback,
            {
                "event": "bootstrap",
                "message": "站点元数据已就绪",
                "query_mode": request.query_mode,
                "total_days": len(query_dates),
            },
        )

        if request.query_mode == "route":
            if request.query_scope == "station":
                if request.from_station_name not in station_name_index:
                    raise RealtimeQueryError(f"unknown station: {request.from_station_name}")
                if request.to_station_name not in station_name_index:
                    raise RealtimeQueryError(f"unknown station: {request.to_station_name}")
            else:
                from_city_name = normalize_city_name(request.from_station_name)
                to_city_name = normalize_city_name(request.to_station_name)
                if from_city_name not in city_name_index:
                    raise RealtimeQueryError(f"unknown city: {request.from_station_name}")
                if to_city_name not in city_name_index:
                    raise RealtimeQueryError(f"unknown city: {request.to_station_name}")
            result = self._run_route_query(
                request=request,
                query_dates=query_dates,
                station_by_code=station_by_code,
                station_name_index=station_name_index,
                city_name_index=city_name_index,
                progress_callback=progress_callback,
            )
        else:
            if request.query_scope == "station":
                if request.from_station_name and request.from_station_name not in station_name_index:
                    raise RealtimeQueryError(f"unknown station: {request.from_station_name}")
                if request.to_station_name and request.to_station_name not in station_name_index:
                    raise RealtimeQueryError(f"unknown station: {request.to_station_name}")
            else:
                station_name = request.from_station_name or request.to_station_name
                if station_name and normalize_city_name(station_name) not in city_name_index:
                    raise RealtimeQueryError(f"unknown city: {station_name}")
            result = self._run_single_head_query(
                request=request,
                query_dates=query_dates,
                progress_callback=progress_callback,
            )

        self._emit(
            progress_callback,
            {
                "event": "completed",
                "message": "实时查询完成",
                "matched_train_count": result["summary"]["matched_train_count"],
            },
        )
        return result

    def _get_station_indexes(
        self,
    ) -> tuple[dict[str, StationRecord], dict[str, str], dict[str, list[StationRecord]]]:
        with self._station_cache_lock:
            if (
                self._station_by_code is None
                or self._station_name_index is None
                or self._city_name_index is None
            ):
                session = create_session()
                station_by_code = self._station_fetcher(session)
                self._station_by_code = station_by_code
                self._station_name_index = build_station_name_index(station_by_code)
                self._city_name_index = build_city_name_index(station_by_code)
            return self._station_by_code, self._station_name_index, self._city_name_index

    def _run_route_query(
        self,
        *,
        request: RealtimeQueryRequest,
        query_dates: list[str],
        station_by_code: dict[str, StationRecord],
        station_name_index: dict[str, str],
        city_name_index: dict[str, list[StationRecord]],
        progress_callback: ProgressCallback | None,
    ) -> dict[str, Any]:
        if request.query_scope == "station":
            route_pairs = [
                (
                    station_name_index[request.from_station_name],
                    station_name_index[request.to_station_name],
                )
            ]
        else:
            from_anchor = choose_city_anchor_station(
                request.from_station_name,
                station_name_index=station_name_index,
                city_name_index=city_name_index,
            )
            to_anchor = choose_city_anchor_station(
                request.to_station_name,
                station_name_index=station_name_index,
                city_name_index=city_name_index,
            )
            route_pairs = [
                (from_anchor.telecode, to_anchor.telecode)
            ]
        daily_results: list[dict[str, Any]] = []
        partial_failures: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=self.route_day_workers) as executor:
            futures = {
                executor.submit(
                    self._query_route_day,
                    request,
                    query_date,
                    route_pairs,
                    station_by_code,
                    progress_callback,
                ): query_date
                for query_date in query_dates
            }
            for future in as_completed(futures):
                query_date = futures[future]
                try:
                    daily_results.append(future.result())
                except Exception as exc:
                    partial_failures.append(
                        {
                            "query_date": query_date,
                            "stage": "querying_date",
                            "error_type": classify_upstream_error(exc),
                            "message": format_upstream_error_message(exc),
                        }
                    )
        daily_results.sort(key=lambda item: item["query_date"])
        partial_failures.sort(key=lambda item: item["query_date"])
        aggregated_results = aggregate_results(request.query_mode, daily_results)
        return {
            "request": {
                "date_from": request.date_from,
                "date_to": request.date_to,
                "query_mode": request.query_mode,
                "query_scope": request.query_scope,
                "from_station_name": request.from_station_name,
                "to_station_name": request.to_station_name,
                "train_code": request.train_code,
                "train_class_name": request.train_class_name,
            },
            "daily_results": daily_results,
            "aggregated_results": aggregated_results,
            "partial_failures": partial_failures,
            "summary": build_overall_summary(
                daily_results=daily_results,
                aggregated_results=aggregated_results,
                partial_failures=partial_failures,
            ),
        }

    def _query_route_day(
        self,
        request: RealtimeQueryRequest,
        query_date: str,
        route_pairs: list[tuple[str, str]],
        station_by_code: dict[str, StationRecord],
        progress_callback: ProgressCallback | None,
    ) -> dict[str, Any]:
        self._emit(
            progress_callback,
            {
                "event": "querying_date",
                "message": f"查询区间 {request.from_station_name} -> {request.to_station_name}",
                "query_date": query_date,
            },
        )
        items: list[dict[str, Any]] = []
        seen_keys: set[tuple[str, str, str]] = set()
        request_from_city = normalize_city_name(request.from_station_name)
        request_to_city = normalize_city_name(request.to_station_name)
        last_error: Exception | None = None
        successful_pair_count = 0
        for from_code, to_code in route_pairs:
            try:
                payload = self._request_with_retry(
                    lambda session, current_from=from_code, current_to=to_code: (
                        self._left_ticket_bootstrapper(session),
                        self._left_ticket_fetcher(session, query_date, current_from, current_to),
                    )[1]
                )
            except Exception as exc:
                last_error = exc
                continue
            successful_pair_count += 1
            rows, route_station_map = parse_left_ticket_payload(payload)
            for row in rows:
                train_code = row.station_train_code.upper()
                train_class_name = normalize_train_class(train_code, "")
                if request.train_code and train_code != request.train_code:
                    continue
                if request.train_class_name and train_class_name != request.train_class_name:
                    continue
                from_station_name = station_by_code.get(
                    row.from_station_code,
                    StationRecord(
                        name=route_station_map.get(row.from_station_code, request.from_station_name),
                        telecode=row.from_station_code,
                    ),
                ).name
                to_station_name = station_by_code.get(
                    row.to_station_code,
                    StationRecord(
                        name=route_station_map.get(row.to_station_code, request.to_station_name),
                        telecode=row.to_station_code,
                    ),
                ).name
                if request.query_scope == "station":
                    if row.from_station_code != from_code or row.to_station_code != to_code:
                        continue
                else:
                    if normalize_city_name(from_station_name) != request_from_city:
                        continue
                    if normalize_city_name(to_station_name) != request_to_city:
                        continue
                item_key = (row.train_no, row.from_station_code, row.to_station_code)
                if item_key in seen_keys:
                    continue
                seen_keys.add(item_key)
                seat_offers = build_seat_offers(row)
                items.append(
                    {
                        "query_date": query_date,
                        "train_no": row.train_no,
                        "train_code": train_code,
                        "train_class_name": train_class_name,
                        "start_station_name": station_by_code.get(
                            row.start_station_code,
                            StationRecord(name=row.start_station_code, telecode=row.start_station_code),
                        ).name,
                        "end_station_name": station_by_code.get(
                            row.end_station_code,
                            StationRecord(name=row.end_station_code, telecode=row.end_station_code),
                        ).name,
                        "query_scope": request.query_scope,
                        "from_station_name": request.from_station_name,
                        "to_station_name": request.to_station_name,
                        "matched_from_station_name": from_station_name,
                        "matched_to_station_name": to_station_name,
                        "depart_time": row.depart_time,
                        "arrive_time": row.arrive_time,
                        "duration": row.duration,
                        "arrive_day_diff": 0,
                        "sale_status": row.sale_status,
                        "can_web_buy": row.can_web_buy,
                        "route_signature": f"{from_code}->{to_code}",
                        "matched_route_signature": f"{row.from_station_code}->{row.to_station_code}",
                        "seat_offers": seat_offers,
                        "min_price": compute_min_price(seat_offers),
                    }
                )
        if successful_pair_count == 0 and last_error is not None:
            raise last_error
        items.sort(
            key=lambda item: (
                item["min_price"] is None,
                item["min_price"] if item["min_price"] is not None else 0,
                item["duration"],
                item["depart_time"],
                item["train_code"],
            )
        )
        return {
            "query_date": query_date,
            "items": items,
            "summary": build_daily_summary(items),
            "failure": None,
        }

    def _run_single_head_query(
        self,
        *,
        request: RealtimeQueryRequest,
        query_dates: list[str],
        progress_callback: ProgressCallback | None,
    ) -> dict[str, Any]:
        station_name = request.from_station_name or request.to_station_name
        daily_results: list[dict[str, Any]] = []
        partial_failures: list[dict[str, Any]] = []
        for query_date in query_dates:
            try:
                daily_results.append(
                    self._query_single_head_day(
                        request=request,
                        query_date=query_date,
                        station_name=station_name,
                        progress_callback=progress_callback,
                    )
                )
            except Exception as exc:
                partial_failures.append(
                    {
                        "query_date": query_date,
                        "stage": "enriching_schedule",
                        "error_type": classify_upstream_error(exc),
                        "message": format_upstream_error_message(exc),
                    }
                )
        aggregated_results = aggregate_results(request.query_mode, daily_results)
        return {
            "request": {
                "date_from": request.date_from,
                "date_to": request.date_to,
                "query_mode": request.query_mode,
                "query_scope": request.query_scope,
                "from_station_name": request.from_station_name,
                "to_station_name": request.to_station_name,
                "train_code": request.train_code,
                "train_class_name": request.train_class_name,
            },
            "daily_results": daily_results,
            "aggregated_results": aggregated_results,
            "partial_failures": partial_failures,
            "summary": build_overall_summary(
                daily_results=daily_results,
                aggregated_results=aggregated_results,
                partial_failures=partial_failures,
            ),
        }

    def _query_single_head_day(
        self,
        *,
        request: RealtimeQueryRequest,
        query_date: str,
        station_name: str,
        progress_callback: ProgressCallback | None,
    ) -> dict[str, Any]:
        self._emit(
            progress_callback,
            {
                "event": "querying_date",
                "message": "抓取车次种子",
                "query_date": query_date,
            },
        )
        seeds_payload = self._request_with_retry(
            lambda session: self._train_seed_fetcher(session, query_date)
        )
        seeds = parse_train_seed(seeds_payload, query_date)
        if request.train_code:
            seeds = [seed for seed in seeds if seed.station_train_code.upper() == request.train_code]
        self._emit(
            progress_callback,
            {
                "event": "enriching_schedule",
                "message": f"补充时刻表，共 {len(seeds)} 列",
                "query_date": query_date,
            },
        )
        items: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=self.train_info_workers) as executor:
            futures = {
                executor.submit(self._fetch_train_info_result, query_date, seed.train_no): seed
                for seed in seeds
            }
            for future in as_completed(futures):
                seed = futures[future]
                try:
                    train_info = future.result()
                except Exception as exc:
                    self._emit(
                        progress_callback,
                        {
                            "event": "failed",
                            "query_date": query_date,
                            "train_code": seed.station_train_code,
                            "message": format_upstream_error_message(exc),
                            "error_type": classify_upstream_error(exc),
                        },
                    )
                    continue
                summary = train_info.summary
                train_class_name = normalize_train_class(
                    summary.station_train_code, summary.train_class_name
                )
                if request.train_class_name and train_class_name != request.train_class_name:
                    continue
                matched_stop = None
                if station_name:
                    if request.query_scope == "city":
                        target_city_name = normalize_city_name(station_name)
                        matched_stop = next(
                            (
                                stop
                                for stop in train_info.stops
                                if normalize_city_name(stop.station_name) == target_city_name
                            ),
                            None,
                        )
                    else:
                        matched_stop = next(
                            (stop for stop in train_info.stops if stop.station_name == station_name),
                            None,
                        )
                    if matched_stop is None:
                        continue
                items.append(
                    {
                        "query_date": query_date,
                        "train_no": summary.train_no,
                        "train_code": summary.station_train_code,
                        "train_class_name": train_class_name,
                        "start_station_name": summary.start_station_name,
                        "end_station_name": summary.end_station_name,
                        "query_scope": request.query_scope,
                        "matched_station_name": matched_stop.station_name if matched_stop else "",
                        "matched_station_no": matched_stop.station_no if matched_stop else "",
                        "matched_arrive_time": matched_stop.arrive_time if matched_stop else "",
                        "matched_depart_time": matched_stop.start_time if matched_stop else "",
                        "depart_time": summary.depart_time,
                        "arrive_time": summary.arrive_time,
                        "duration": summary.duration,
                        "stop_count": len(train_info.stops),
                        "detail_available": True,
                        "seat_offers": [],
                        "sale_status": "",
                        "can_web_buy": "",
                        "route_signature": "",
                        "min_price": None,
                    }
                )
        items.sort(key=lambda item: (item["depart_time"], item["duration"], item["train_code"]))
        return {
            "query_date": query_date,
            "items": items,
            "summary": build_daily_summary(items),
            "failure": None,
        }

    def _fetch_train_info_result(self, query_date: str, train_no: str):
        payload = self._request_with_retry(
            lambda session: self._train_info_fetcher(session, query_date, train_no)
        )
        return parse_train_info(payload, query_date, train_no)

    def _request_with_retry(self, fn: Callable[[Any], Any]) -> Any:
        last_error: Exception | None = None
        for attempt in range(3):
            session = create_session()
            try:
                return fn(session)
            except Exception as exc:
                last_error = exc
                if attempt == 2:
                    raise
                time.sleep(0.5 * (2**attempt))
        raise RuntimeError(str(last_error))

    @staticmethod
    def _emit(progress_callback: ProgressCallback | None, event: dict[str, Any]) -> None:
        if progress_callback is not None:
            progress_callback(event)


class RealtimeJobManager:
    """Run realtime queries in background threads and expose event streams."""

    def __init__(
        self,
        service: RealtimeQueryService,
        *,
        job_ttl_seconds: int = DEFAULT_JOB_TTL_SECONDS,
    ) -> None:
        self._service = service
        self._job_ttl_seconds = job_ttl_seconds
        self._jobs: dict[str, RealtimeJob] = {}
        self._lock = threading.Lock()

    def create_job(self, payload: dict[str, Any]) -> RealtimeJob:
        """Create and start a realtime query job."""

        self.cleanup_expired_jobs()
        request = normalize_realtime_request(payload)
        now = datetime.now(timezone.utc).isoformat()
        job = RealtimeJob(
            job_id=uuid.uuid4().hex,
            request={
                "date_from": request.date_from,
                "date_to": request.date_to,
                "query_mode": request.query_mode,
                "query_scope": request.query_scope,
                "from_station_name": request.from_station_name,
                "to_station_name": request.to_station_name,
                "train_code": request.train_code,
                "train_class_name": request.train_class_name,
            },
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._jobs[job.job_id] = job
        self._append_event(job, {"event": "queued", "message": "任务已创建"})
        threading.Thread(target=self._run_job, args=(job, request), daemon=True).start()
        return job

    def get_job(self, job_id: str) -> RealtimeJob:
        """Return one job or raise KeyError."""

        self.cleanup_expired_jobs()
        with self._lock:
            return self._jobs[job_id]

    def export_job(self, job_id: str, format_name: str) -> tuple[str | bytes, str]:
        """Return one completed job as CSV or JSON text."""

        job = self.get_job(job_id)
        if job.status != "completed" or job.result is None:
            raise RealtimeQueryError("job is not completed yet")
        if format_name == "json":
            return json.dumps(job.result, ensure_ascii=False, indent=2), "application/json; charset=utf-8"
        if format_name != "csv":
            raise RealtimeQueryError("format must be csv or json")
        csv_buffer = io.StringIO()
        fieldnames = [
            "query_date",
            "train_code",
            "train_class_name",
            "start_station_name",
            "end_station_name",
            "from_station_name",
            "to_station_name",
            "matched_station_name",
            "depart_time",
            "arrive_time",
            "duration",
            "sale_status",
            "can_web_buy",
            "route_signature",
            "min_price",
        ]
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        for daily in job.result.get("daily_results", []):
            for item in daily.get("items", []):
                writer.writerow(
                    {
                        "query_date": item.get("query_date", ""),
                        "train_code": item.get("train_code", ""),
                        "train_class_name": item.get("train_class_name", ""),
                        "start_station_name": item.get("start_station_name", ""),
                        "end_station_name": item.get("end_station_name", ""),
                        "from_station_name": item.get("from_station_name", ""),
                        "to_station_name": item.get("to_station_name", ""),
                        "matched_station_name": item.get("matched_station_name", ""),
                        "depart_time": item.get("depart_time", ""),
                        "arrive_time": item.get("arrive_time", ""),
                        "duration": item.get("duration", ""),
                        "sale_status": item.get("sale_status", ""),
                        "can_web_buy": item.get("can_web_buy", ""),
                        "route_signature": item.get("route_signature", ""),
                        "min_price": item.get("min_price", ""),
                    }
                )
        return csv_buffer.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8"

    def iter_events(self, job_id: str):
        """Yield SSE payload chunks for one job."""

        job = self.get_job(job_id)
        index = 0
        while True:
            with job.condition:
                if index >= len(job.events) and job.status not in FINAL_JOB_STATUSES:
                    job.condition.wait(timeout=10)
                    if index >= len(job.events):
                        yield ": keep-alive\n\n"
                        continue
                while index < len(job.events):
                    event = job.events[index]
                    index += 1
                    yield (
                        f"event: {event['event']}\n"
                        f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    )
                if job.status in FINAL_JOB_STATUSES and index >= len(job.events):
                    break

    def cleanup_expired_jobs(self) -> None:
        """Remove completed jobs older than the configured TTL."""

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._job_ttl_seconds)
        with self._lock:
            expired_ids = []
            for job_id, job in self._jobs.items():
                created_at = datetime.fromisoformat(job.created_at)
                if job.status in FINAL_JOB_STATUSES and created_at < cutoff:
                    expired_ids.append(job_id)
            for job_id in expired_ids:
                self._jobs.pop(job_id, None)

    def _run_job(self, job: RealtimeJob, request: RealtimeQueryRequest) -> None:
        self._set_status(job, "running")
        try:
            result = self._service.run_query(
                request,
                progress_callback=lambda event: self._append_event(job, event),
            )
        except Exception as exc:
            job.error = format_upstream_error_message(exc)
            self._append_event(
                job,
                {
                    "event": "failed",
                    "message": format_upstream_error_message(exc),
                    "error_type": classify_upstream_error(exc),
                },
            )
            self._set_status(job, "failed")
            return
        job.result = result
        self._set_status(job, "completed")

    def _set_status(self, job: RealtimeJob, status: str) -> None:
        job.status = status
        job.updated_at = datetime.now(timezone.utc).isoformat()
        with job.condition:
            job.condition.notify_all()

    def _append_event(self, job: RealtimeJob, event: dict[str, Any]) -> None:
        payload = {
            "event": event["event"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **event,
        }
        job.events.append(payload)
        job.updated_at = payload["timestamp"]
        with job.condition:
            job.condition.notify_all()
