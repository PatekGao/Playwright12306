"""Import normalized artifacts into a local SQLite search database."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from playwright12306.search_db import connect_db, initialize_db


@dataclass(frozen=True)
class ImportResult:
    """Summary of one artifacts import."""

    query_date: str
    train_count: int
    stop_count: int
    route_count: int
    seat_price_count: int
    db_path: Path


def import_artifacts(*, artifacts_dir: Path, db_path: Path) -> ImportResult:
    """Import one artifacts directory into a SQLite database.

    Args:
        artifacts_dir: Directory that contains `normalized/*.csv`.
        db_path: Target SQLite database path.

    Returns:
        Summary of inserted rows.

    Raises:
        FileNotFoundError: If the normalized CSV files are missing.
        ValueError: If the imported files do not contain a valid query date.
    """

    normalized_dir = artifacts_dir / "normalized"
    trains_rows = _deduplicate_rows(
        _read_csv_rows(normalized_dir / "trains.csv"),
        ["query_date", "train_no"],
    )
    stops_rows = _deduplicate_rows(
        _read_csv_rows(normalized_dir / "stops.csv"),
        ["query_date", "train_no", "station_no"],
    )
    routes_rows = _deduplicate_rows(
        _read_csv_rows(normalized_dir / "routes.csv"),
        ["query_date", "from_station_code", "to_station_code"],
    )
    query_date = _extract_query_date(trains_rows)
    seat_price_rows = _deduplicate_rows(
        _build_seat_price_rows(trains_rows),
        ["query_date", "train_no", "route_signature", "seat_code"],
    )
    imported_at = datetime.now(timezone.utc).isoformat()

    connection = connect_db(db_path)
    try:
        initialize_db(connection)
        with connection:
            connection.execute("delete from seat_prices where query_date = ?", (query_date,))
            connection.execute("delete from routes where query_date = ?", (query_date,))
            connection.execute("delete from stops where query_date = ?", (query_date,))
            connection.execute("delete from trains where query_date = ?", (query_date,))

            connection.executemany(
                """
                insert into trains (
                    query_date, train_no, train_code, station_train_code, train_class_name,
                    start_station_name, end_station_name, from_station_name, to_station_name,
                    depart_time, arrive_time, duration, arrive_day_diff,
                    from_station_code, to_station_code, seat_price_json,
                    stop_count, route_signature, sale_status, can_web_buy, seat_inventory_json
                ) values (
                    :query_date, :train_no, :train_code, :station_train_code, :train_class_name,
                    :start_station_name, :end_station_name, :from_station_name, :to_station_name,
                    :depart_time, :arrive_time, :duration, :arrive_day_diff,
                    :from_station_code, :to_station_code, :seat_price_json,
                    :stop_count, :route_signature, :sale_status, :can_web_buy, :seat_inventory_json
                )
                """,
                [_normalize_train_row(row) for row in trains_rows],
            )
            connection.executemany(
                """
                insert into stops (
                    query_date, train_no, station_train_code, station_no, station_name,
                    arrive_time, start_time, running_time, arrive_day_diff, is_start, is_end
                ) values (
                    :query_date, :train_no, :station_train_code, :station_no, :station_name,
                    :arrive_time, :start_time, :running_time, :arrive_day_diff, :is_start, :is_end
                )
                """,
                [_normalize_stop_row(row) for row in stops_rows],
            )
            connection.executemany(
                """
                insert into routes (
                    query_date, from_station_code, to_station_code, result_count, fetched_at
                ) values (
                    :query_date, :from_station_code, :to_station_code, :result_count, :fetched_at
                )
                """,
                [_normalize_route_row(row) for row in routes_rows],
            )
            connection.executemany(
                """
                insert into seat_prices (
                    query_date, train_no, route_signature, seat_code, seat_name, price
                ) values (
                    :query_date, :train_no, :route_signature, :seat_code, :seat_name, :price
                )
                """,
                seat_price_rows,
            )
            connection.execute(
                """
                insert into import_batches (
                    query_date, source_dir, imported_at, train_count, stop_count, route_count, seat_price_count
                ) values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_date,
                    str(artifacts_dir.resolve()),
                    imported_at,
                    len(trains_rows),
                    len(stops_rows),
                    len(routes_rows),
                    len(seat_price_rows),
                ),
            )
    finally:
        connection.close()

    return ImportResult(
        query_date=query_date,
        train_count=len(trains_rows),
        stop_count=len(stops_rows),
        route_count=len(routes_rows),
        seat_price_count=len(seat_price_rows),
        db_path=db_path,
    )


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing normalized file: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _extract_query_date(rows: list[dict[str, str]]) -> str:
    if not rows:
        raise ValueError("trains.csv is empty")
    query_date = str(rows[0].get("query_date", "")).strip()
    if not query_date:
        raise ValueError("query_date is missing from trains.csv")
    return query_date


def _build_seat_price_rows(trains_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for row in trains_rows:
        query_date = str(row.get("query_date", "")).strip()
        train_no = str(row.get("train_no", "")).strip()
        route_signature = str(row.get("route_signature", "")).strip()
        raw_prices = str(row.get("seat_price_json", "")).strip()
        if not raw_prices:
            continue
        for price_item in json.loads(raw_prices):
            items.append(
                {
                    "query_date": query_date,
                    "train_no": train_no,
                    "route_signature": route_signature,
                    "seat_code": str(price_item.get("code", "")).strip(),
                    "seat_name": str(price_item.get("name", "")).strip(),
                    "price": float(price_item.get("price", 0)),
                }
            )
    return items


def _normalize_train_row(row: dict[str, str]) -> dict[str, object]:
    return {
        "query_date": str(row.get("query_date", "")).strip(),
        "train_no": str(row.get("train_no", "")).strip(),
        "train_code": str(row.get("train_code", "")).strip(),
        "station_train_code": str(row.get("station_train_code", "")).strip(),
        "train_class_name": str(row.get("train_class_name", "")).strip(),
        "start_station_name": str(row.get("start_station_name", "")).strip(),
        "end_station_name": str(row.get("end_station_name", "")).strip(),
        "from_station_name": str(row.get("from_station_name", "")).strip(),
        "to_station_name": str(row.get("to_station_name", "")).strip(),
        "depart_time": str(row.get("depart_time", "")).strip(),
        "arrive_time": str(row.get("arrive_time", "")).strip(),
        "duration": str(row.get("duration", "")).strip(),
        "arrive_day_diff": int(str(row.get("arrive_day_diff", "0")).strip() or 0),
        "from_station_code": str(row.get("from_station_code", "")).strip(),
        "to_station_code": str(row.get("to_station_code", "")).strip(),
        "seat_price_json": str(row.get("seat_price_json", "")).strip(),
        "stop_count": int(str(row.get("stop_count", "0")).strip() or 0),
        "route_signature": str(row.get("route_signature", "")).strip(),
        "sale_status": str(row.get("sale_status", "")).strip(),
        "can_web_buy": str(row.get("can_web_buy", "")).strip(),
        "seat_inventory_json": str(row.get("seat_inventory_json", "")).strip() or None,
    }


def _normalize_stop_row(row: dict[str, str]) -> dict[str, object]:
    return {
        "query_date": str(row.get("query_date", "")).strip(),
        "train_no": str(row.get("train_no", "")).strip(),
        "station_train_code": str(row.get("station_train_code", "")).strip(),
        "station_no": int(str(row.get("station_no", "0")).strip() or 0),
        "station_name": str(row.get("station_name", "")).strip(),
        "arrive_time": str(row.get("arrive_time", "")).strip(),
        "start_time": str(row.get("start_time", "")).strip(),
        "running_time": str(row.get("running_time", "")).strip(),
        "arrive_day_diff": int(str(row.get("arrive_day_diff", "0")).strip() or 0),
        "is_start": str(row.get("is_start", "")).strip(),
        "is_end": str(row.get("is_end", "")).strip(),
    }


def _normalize_route_row(row: dict[str, str]) -> dict[str, object]:
    return {
        "query_date": str(row.get("query_date", "")).strip(),
        "from_station_code": str(row.get("from_station_code", "")).strip(),
        "to_station_code": str(row.get("to_station_code", "")).strip(),
        "result_count": int(str(row.get("result_count", "0")).strip() or 0),
        "fetched_at": str(row.get("fetched_at", "")).strip(),
    }


def _deduplicate_rows(
    rows: list[dict[str, object]],
    key_fields: list[str],
) -> list[dict[str, object]]:
    deduplicated: list[dict[str, object]] = []
    seen: set[tuple[str, ...]] = set()
    for row in rows:
        key = tuple(str(row.get(field, "")).strip() for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(row)
    return deduplicated
