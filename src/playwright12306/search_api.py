"""FastAPI application for local train search queries."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import sqlite3
from typing import Any
from urllib.parse import quote

from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from playwright12306.realtime import (
    RealtimeJobManager,
    RealtimeQueryError,
    RealtimeQueryService,
)
from playwright12306.search_db import connect_db


SORT_COLUMN_MAP = {
    "depart_time": "t.depart_time",
    "arrive_time": "t.arrive_time",
    "duration": "t.duration",
    "train_code": "t.train_code",
    "min_price": "min_price",
}


def _sanitize_filename_part(value: str) -> str:
    """Convert one user-facing value into a filename-safe token."""

    text = (value or "").strip()
    if not text:
        return ""
    for char in '\\/:*?"<>|':
        text = text.replace(char, "-")
    return text.replace(" ", "_")


def _build_download_filename(stem: str, suffix: str = ".csv") -> str:
    """Build a browser-friendly Content-Disposition header value."""

    safe_stem = _sanitize_filename_part(stem) or "export"
    fallback = f"{safe_stem.encode('ascii', 'ignore').decode('ascii') or 'export'}{suffix}"
    utf8_name = f"{safe_stem}{suffix}"
    return f"attachment; filename={json.dumps(fallback)}; filename*=UTF-8''{quote(utf8_name)}"


def _build_realtime_export_filename(job: Any) -> str:
    """Build a readable realtime export filename from one job request."""

    request = job.request
    stem_parts = [
        "realtime",
        request.get("date_from", ""),
    ]
    if request.get("date_to") and request.get("date_to") != request.get("date_from"):
        stem_parts[-1] = f"{request['date_from']}_to_{request['date_to']}"
    stem_parts.append("站点对" if request.get("query_scope") == "station" else "城市对")
    stem_parts.append("区间" if request.get("query_mode") == "route" else "单头")
    if request.get("from_station_name") or request.get("to_station_name"):
        route_part = f"{request.get('from_station_name', '')}-{request.get('to_station_name', '')}".strip("-")
        if route_part:
            stem_parts.append(route_part)
    if request.get("train_code"):
        stem_parts.append(request["train_code"])
    if request.get("train_class_name"):
        stem_parts.append(request["train_class_name"])
    return "_".join(part for part in stem_parts if part)


def _build_train_export_filename(
    *,
    query_date: str,
    train_code: str | None,
    start_station_name: str | None,
    end_station_name: str | None,
    train_class_name: str | None,
) -> str:
    """Build a readable local-train export filename from active filters."""

    stem_parts = ["trains", query_date]
    if start_station_name or end_station_name:
        route_part = f"{start_station_name or ''}-{end_station_name or ''}".strip("-")
        if route_part:
            stem_parts.append(route_part)
    if train_code:
        stem_parts.append(train_code)
    if train_class_name:
        stem_parts.append(train_class_name)
    return "_".join(part for part in stem_parts if part)


def create_app(
    db_path: Path,
    *,
    realtime_service: RealtimeQueryService | None = None,
    realtime_manager: RealtimeJobManager | None = None,
    web_dist: Path | None = None,
) -> FastAPI:
    """Create the FastAPI app bound to a local SQLite database."""

    app = FastAPI(title="12306 Local Search API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    service = realtime_service or RealtimeQueryService()
    manager = realtime_manager or RealtimeJobManager(service)

    def get_connection() -> sqlite3.Connection:
        if not db_path.exists():
            raise HTTPException(
                status_code=503,
                detail=f"database not found at {db_path}, run import script first",
            )
        connection = connect_db(db_path)
        try:
            yield connection
        finally:
            connection.close()

    @app.get("/api/meta/summary")
    def meta_summary(connection: sqlite3.Connection = Depends(get_connection)) -> dict[str, Any]:
        query_dates = [
            row["query_date"]
            for row in connection.execute(
                "select distinct query_date from import_batches order by query_date"
            ).fetchall()
        ]
        total_trains = connection.execute("select count(*) as count from trains").fetchone()["count"]
        total_stops = connection.execute("select count(*) as count from stops").fetchone()["count"]
        latest_imported_at = connection.execute(
            "select max(imported_at) as imported_at from import_batches"
        ).fetchone()["imported_at"]
        return {
            "query_dates": query_dates,
            "total_trains": total_trains,
            "total_stops": total_stops,
            "latest_imported_at": latest_imported_at,
        }

    @app.get("/api/meta/options")
    def meta_options(connection: sqlite3.Connection = Depends(get_connection)) -> dict[str, Any]:
        query_dates = [
            row["query_date"]
            for row in connection.execute("select distinct query_date from trains order by query_date").fetchall()
        ]
        train_classes = [
            row["train_class_name"]
            for row in connection.execute(
                "select distinct train_class_name from trains order by train_class_name"
            ).fetchall()
        ]
        stations = [
            row["station_name"]
            for row in connection.execute(
                "select distinct station_name from stops order by station_name"
            ).fetchall()
        ]
        seat_names = [
            row["seat_name"]
            for row in connection.execute(
                "select distinct seat_name from seat_prices order by seat_name"
            ).fetchall()
        ]
        return {
            "query_dates": query_dates,
            "train_classes": train_classes,
            "stations": stations,
            "seat_names": seat_names,
        }

    @app.get("/api/realtime/meta/stations")
    def realtime_stations() -> dict[str, Any]:
        try:
            return {
                "stations": service.list_station_names(),
                "cities": service.list_city_names(),
            }
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/api/realtime/jobs")
    def create_realtime_job(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
        try:
            job = manager.create_job(payload)
        except RealtimeQueryError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"job_id": job.job_id, "status": job.status, "request": job.request}

    @app.get("/api/realtime/jobs/{job_id}")
    def get_realtime_job(job_id: str) -> dict[str, Any]:
        try:
            return manager.get_job(job_id).serialize()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc

    @app.get("/api/realtime/jobs/{job_id}/events")
    def stream_realtime_events(job_id: str):
        try:
            iterator = manager.iter_events(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc
        return StreamingResponse(iterator, media_type="text/event-stream")

    @app.get("/api/realtime/jobs/{job_id}/export")
    def export_realtime_job(job_id: str, format: str = Query(default="csv")):
        try:
            payload, media_type = manager.export_job(job_id, format)
            job = manager.get_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc
        except RealtimeQueryError as exc:
            status_code = 409 if "not completed" in str(exc) else 422
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        headers = {}
        if format == "csv":
            headers["Content-Disposition"] = _build_download_filename(
                _build_realtime_export_filename(job)
            )
        return StreamingResponse(iter([payload]), media_type=media_type, headers=headers)

    @app.get("/api/realtime/trains/{query_date}/{train_no}")
    def realtime_train_detail(
        query_date: str,
        train_no: str,
        from_station_name: str | None = None,
        to_station_name: str | None = None,
    ) -> dict[str, Any]:
        try:
            return service.get_train_detail(
                query_date=query_date,
                train_no=train_no,
                from_station_name=(from_station_name or "").strip(),
                to_station_name=(to_station_name or "").strip(),
            )
        except RealtimeQueryError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/trains")
    def list_trains(
        query_date: str,
        train_code: str | None = None,
        start_station_name: str | None = None,
        end_station_name: str | None = None,
        train_class_name: str | None = None,
        seat_name: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sale_status: str | None = None,
        depart_time_from: str | None = None,
        depart_time_to: str | None = None,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=200),
        sort_by: str = Query(default="depart_time"),
        sort_order: str = Query(default="asc"),
        connection: sqlite3.Connection = Depends(get_connection),
    ) -> dict[str, Any]:
        query_result = _query_trains(
            connection=connection,
            query_date=query_date,
            train_code=train_code,
            start_station_name=start_station_name,
            end_station_name=end_station_name,
            train_class_name=train_class_name,
            seat_name=seat_name,
            min_price=min_price,
            max_price=max_price,
            sale_status=sale_status,
            depart_time_from=depart_time_from,
            depart_time_to=depart_time_to,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return query_result

    @app.get("/api/trains/export")
    def export_trains(
        query_date: str,
        format: str = Query(default="csv"),
        train_code: str | None = None,
        start_station_name: str | None = None,
        end_station_name: str | None = None,
        train_class_name: str | None = None,
        seat_name: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sale_status: str | None = None,
        depart_time_from: str | None = None,
        depart_time_to: str | None = None,
        sort_by: str = Query(default="depart_time"),
        sort_order: str = Query(default="asc"),
        connection: sqlite3.Connection = Depends(get_connection),
    ):
        query_result = _query_trains(
            connection=connection,
            query_date=query_date,
            train_code=train_code,
            start_station_name=start_station_name,
            end_station_name=end_station_name,
            train_class_name=train_class_name,
            seat_name=seat_name,
            min_price=min_price,
            max_price=max_price,
            sale_status=sale_status,
            depart_time_from=depart_time_from,
            depart_time_to=depart_time_to,
            page=1,
            page_size=100_000,
            sort_by=sort_by,
            sort_order=sort_order,
            include_matched_prices=False,
        )
        items = query_result["items"]
        if format == "json":
            return JSONResponse(items)
        if format != "csv":
            raise HTTPException(status_code=422, detail="format must be csv or json")
        if not items:
            header = "query_date,train_no,train_code,train_class_name,start_station_name,end_station_name,depart_time,arrive_time,duration,min_price,route_signature,sale_status\n".encode("utf-8-sig")
            return StreamingResponse(iter([header]), media_type="text/csv; charset=utf-8")
        csv_buffer = io.StringIO()
        fieldnames = list(items[0].keys())
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            row = {
                key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                for key, value in item.items()
            }
            writer.writerow(row)
        return StreamingResponse(
            iter([csv_buffer.getvalue().encode("utf-8-sig")]),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": _build_download_filename(
                    _build_train_export_filename(
                        query_date=query_date,
                        train_code=train_code,
                        start_station_name=start_station_name,
                        end_station_name=end_station_name,
                        train_class_name=train_class_name,
                    )
                )
            },
        )

    @app.get("/api/trains/{query_date}/{train_no}")
    def train_detail(
        query_date: str,
        train_no: str,
        connection: sqlite3.Connection = Depends(get_connection),
    ) -> dict[str, Any]:
        train_row = connection.execute(
            "select * from trains where query_date = ? and train_no = ?",
            (query_date, train_no),
        ).fetchone()
        if train_row is None:
            raise HTTPException(status_code=404, detail="train not found")
        stops = [
            dict(row)
            for row in connection.execute(
                """
                select * from stops
                where query_date = ? and train_no = ?
                order by station_no
                """,
                (query_date, train_no),
            ).fetchall()
        ]
        seat_prices = [
            dict(row)
            for row in connection.execute(
                """
                select seat_code, seat_name, price, route_signature
                from seat_prices
                where query_date = ? and train_no = ?
                order by price asc, seat_code asc
                """,
                (query_date, train_no),
            ).fetchall()
        ]
        return {
            "train": _serialize_train_row(dict(train_row)),
            "stops": stops,
            "seat_prices": seat_prices,
            "route_signature": train_row["route_signature"],
        }

    resolved_web_dist = web_dist or Path(__file__).resolve().parents[2] / "web" / "dist"
    if resolved_web_dist.exists():
        assets_dir = resolved_web_dist / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="web-assets")

        @app.get("/", include_in_schema=False)
        def spa_index():
            return FileResponse(resolved_web_dist / "index.html")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa_catch_all(full_path: str):
            candidate = resolved_web_dist / full_path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(resolved_web_dist / "index.html")

    return app


def _query_trains(
    *,
    connection: sqlite3.Connection,
    query_date: str,
    train_code: str | None,
    start_station_name: str | None,
    end_station_name: str | None,
    train_class_name: str | None,
    seat_name: str | None,
    min_price: float | None,
    max_price: float | None,
    sale_status: str | None,
    depart_time_from: str | None,
    depart_time_to: str | None,
    page: int,
    page_size: int,
    sort_by: str,
    sort_order: str,
    include_matched_prices: bool = True,
) -> dict[str, Any]:
    if sort_by not in SORT_COLUMN_MAP:
        raise HTTPException(status_code=422, detail="unsupported sort_by")
    if sort_order.lower() not in {"asc", "desc"}:
        raise HTTPException(status_code=422, detail="sort_order must be asc or desc")

    base_conditions = ["t.query_date = :query_date"]
    params: dict[str, Any] = {"query_date": query_date}

    if train_code:
        base_conditions.append("t.train_code like :train_code")
        params["train_code"] = f"%{train_code.strip()}%"
    if start_station_name and end_station_name:
        params["start_station_name"] = f"%{start_station_name.strip()}%"
        params["end_station_name"] = f"%{end_station_name.strip()}%"
        base_conditions.append(
            """
            exists (
                select 1
                from stops s_from
                join stops s_to
                  on s_to.query_date = s_from.query_date
                 and s_to.train_no = s_from.train_no
                where s_from.query_date = t.query_date
                  and s_from.train_no = t.train_no
                  and s_from.station_name like :start_station_name
                  and s_to.station_name like :end_station_name
                  and s_from.station_no < s_to.station_no
            )
            """
        )
    elif start_station_name:
        params["start_station_name"] = f"%{start_station_name.strip()}%"
        base_conditions.append(
            """
            exists (
                select 1
                from stops s_from
                where s_from.query_date = t.query_date
                  and s_from.train_no = t.train_no
                  and s_from.station_name like :start_station_name
            )
            """
        )
    elif end_station_name:
        params["end_station_name"] = f"%{end_station_name.strip()}%"
        base_conditions.append(
            """
            exists (
                select 1
                from stops s_to
                where s_to.query_date = t.query_date
                  and s_to.train_no = t.train_no
                  and s_to.station_name like :end_station_name
            )
            """
        )
    if train_class_name:
        base_conditions.append("t.train_class_name = :train_class_name")
        params["train_class_name"] = train_class_name.strip()
    if sale_status:
        base_conditions.append("t.sale_status = :sale_status")
        params["sale_status"] = sale_status.strip()
    if depart_time_from:
        base_conditions.append("t.depart_time >= :depart_time_from")
        params["depart_time_from"] = depart_time_from.strip()
    if depart_time_to:
        base_conditions.append("t.depart_time <= :depart_time_to")
        params["depart_time_to"] = depart_time_to.strip()

    price_conditions = ["sp.query_date = t.query_date", "sp.train_no = t.train_no"]
    if seat_name:
        price_conditions.append("sp.seat_name = :seat_name")
        params["seat_name"] = seat_name.strip()
    if min_price is not None:
        price_conditions.append("sp.price >= :min_price")
        params["min_price"] = min_price
    if max_price is not None:
        price_conditions.append("sp.price <= :max_price")
        params["max_price"] = max_price
    if seat_name or min_price is not None or max_price is not None:
        base_conditions.append(
            f"exists (select 1 from seat_prices sp where {' and '.join(price_conditions)})"
        )

    where_sql = " and ".join(base_conditions)
    min_price_sql = (
        "select min(sp.price) from seat_prices sp where " + " and ".join(price_conditions)
    )
    count_sql = f"select count(*) as count from trains t where {where_sql}"
    total = connection.execute(count_sql, params).fetchone()["count"]

    summary_sql = f"""
        with filtered as (
            select t.query_date, t.train_no, ({min_price_sql}) as min_price
            from trains t
            where {where_sql}
        )
        select count(*) as train_count, min(min_price) as min_price, max(min_price) as max_price
        from filtered
    """
    summary_row = connection.execute(summary_sql, params).fetchone()
    page_params = dict(params)
    page_params["limit"] = page_size
    page_params["offset"] = (page - 1) * page_size
    order_sql = f"{SORT_COLUMN_MAP[sort_by]} {sort_order.upper()}, t.train_code ASC"
    items_sql = f"""
        select t.*, ({min_price_sql}) as min_price
        from trains t
        where {where_sql}
        order by {order_sql}
        limit :limit offset :offset
    """
    rows = [dict(row) for row in connection.execute(items_sql, page_params).fetchall()]
    items = []
    for row in rows:
        item = _serialize_train_row(row)
        item["min_price"] = float(row["min_price"]) if row["min_price"] is not None else None
        if include_matched_prices:
            item["matched_seat_prices"] = _fetch_matched_seat_prices(
                connection=connection,
                query_date=query_date,
                train_no=row["train_no"],
                seat_name=seat_name,
                min_price=min_price,
                max_price=max_price,
            )
        items.append(item)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "summary": {
            "query_date": query_date,
            "total_trains": summary_row["train_count"],
            "matched_prices": summary_row["train_count"],
            "min_price": float(summary_row["min_price"]) if summary_row["min_price"] is not None else None,
            "max_price": float(summary_row["max_price"]) if summary_row["max_price"] is not None else None,
        },
    }


def _fetch_matched_seat_prices(
    *,
    connection: sqlite3.Connection,
    query_date: str,
    train_no: str,
    seat_name: str | None,
    min_price: float | None,
    max_price: float | None,
) -> list[dict[str, Any]]:
    clauses = ["query_date = ?", "train_no = ?"]
    params: list[Any] = [query_date, train_no]
    if seat_name:
        clauses.append("seat_name = ?")
        params.append(seat_name.strip())
    if min_price is not None:
        clauses.append("price >= ?")
        params.append(min_price)
    if max_price is not None:
        clauses.append("price <= ?")
        params.append(max_price)
    rows = connection.execute(
        f"""
        select seat_code, seat_name, price
        from seat_prices
        where {' and '.join(clauses)}
        order by price asc, seat_code asc
        """,
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def _serialize_train_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "query_date": row["query_date"],
        "train_no": row["train_no"],
        "train_code": row["train_code"],
        "station_train_code": row["station_train_code"],
        "train_class_name": row["train_class_name"],
        "start_station_name": row["start_station_name"],
        "end_station_name": row["end_station_name"],
        "from_station_name": row["from_station_name"],
        "to_station_name": row["to_station_name"],
        "depart_time": row["depart_time"],
        "arrive_time": row["arrive_time"],
        "duration": row["duration"],
        "arrive_day_diff": row["arrive_day_diff"],
        "from_station_code": row["from_station_code"],
        "to_station_code": row["to_station_code"],
        "seat_price_json": row["seat_price_json"],
        "stop_count": row["stop_count"],
        "route_signature": row["route_signature"],
        "sale_status": row["sale_status"],
        "can_web_buy": row["can_web_buy"],
        "seat_inventory_json": row["seat_inventory_json"],
    }
