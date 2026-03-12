"""SQLite helpers for the local train search tool."""

from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_STATEMENTS = [
    """
    create table if not exists trains (
        query_date text not null,
        train_no text not null,
        train_code text not null,
        station_train_code text not null,
        train_class_name text not null,
        start_station_name text not null,
        end_station_name text not null,
        from_station_name text not null,
        to_station_name text not null,
        depart_time text not null,
        arrive_time text not null,
        duration text not null,
        arrive_day_diff integer not null,
        from_station_code text not null,
        to_station_code text not null,
        seat_price_json text not null,
        stop_count integer not null,
        route_signature text not null,
        sale_status text not null default '',
        can_web_buy text not null default '',
        seat_inventory_json text,
        primary key (query_date, train_no)
    )
    """,
    """
    create table if not exists stops (
        query_date text not null,
        train_no text not null,
        station_train_code text not null,
        station_no integer not null,
        station_name text not null,
        arrive_time text not null,
        start_time text not null,
        running_time text not null,
        arrive_day_diff integer not null,
        is_start text not null default '',
        is_end text not null default '',
        primary key (query_date, train_no, station_no)
    )
    """,
    """
    create table if not exists routes (
        query_date text not null,
        from_station_code text not null,
        to_station_code text not null,
        result_count integer not null,
        fetched_at text not null,
        primary key (query_date, from_station_code, to_station_code)
    )
    """,
    """
    create table if not exists seat_prices (
        query_date text not null,
        train_no text not null,
        route_signature text not null,
        seat_code text not null,
        seat_name text not null,
        price real not null,
        primary key (query_date, train_no, route_signature, seat_code)
    )
    """,
    """
    create table if not exists import_batches (
        id integer primary key autoincrement,
        query_date text not null,
        source_dir text not null,
        imported_at text not null,
        train_count integer not null,
        stop_count integer not null,
        route_count integer not null,
        seat_price_count integer not null
    )
    """,
]


INDEX_STATEMENTS = [
    "create index if not exists idx_trains_query_date_train_code on trains(query_date, train_code)",
    "create index if not exists idx_trains_query_date_station_pair on trains(query_date, start_station_name, end_station_name)",
    "create index if not exists idx_trains_query_date_class on trains(query_date, train_class_name)",
    "create index if not exists idx_trains_query_date_depart_time on trains(query_date, depart_time)",
    "create index if not exists idx_stops_query_date_station on stops(query_date, station_name, train_no)",
    "create index if not exists idx_seat_prices_query_date_name_price on seat_prices(query_date, seat_name, price)",
]


def connect_db(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with row access by column name."""

    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_db(connection: sqlite3.Connection) -> None:
    """Create tables and indexes required by the search tool."""

    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)
    for statement in INDEX_STATEMENTS:
        connection.execute(statement)
    connection.commit()
