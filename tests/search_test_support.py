from __future__ import annotations

import csv
import json
from pathlib import Path


def write_sample_artifacts_dir(root: Path) -> Path:
    """Create a minimal artifacts directory for importer and API tests."""

    normalized = root / "normalized"
    normalized.mkdir(parents=True, exist_ok=True)

    trains_rows = [
        {
            "query_date": "2026-03-18",
            "train_no": "24000000G10L",
            "train_code": "G1",
            "station_train_code": "G1",
            "train_class_name": "高速",
            "start_station_name": "北京南",
            "end_station_name": "上海虹桥",
            "from_station_name": "北京南",
            "to_station_name": "上海虹桥",
            "depart_time": "07:00",
            "arrive_time": "11:30",
            "duration": "04:30",
            "arrive_day_diff": "0",
            "from_station_code": "VNP",
            "to_station_code": "AOH",
            "seat_price_json": json.dumps(
                [
                    {"code": "O", "name": "二等座", "price": "553.0"},
                    {"code": "M", "name": "一等座", "price": "933.0"},
                ],
                ensure_ascii=False,
            ),
            "stop_count": "3",
            "route_signature": "VNP->AOH",
            "sale_status": "预订",
            "can_web_buy": "Y",
            "seat_inventory_json": "",
        },
        {
            "query_date": "2026-03-18",
            "train_no": "24000000G20X",
            "train_code": "G2",
            "station_train_code": "G2",
            "train_class_name": "高速",
            "start_station_name": "杭州东",
            "end_station_name": "上海虹桥",
            "from_station_name": "杭州东",
            "to_station_name": "上海虹桥",
            "depart_time": "08:00",
            "arrive_time": "09:10",
            "duration": "01:10",
            "arrive_day_diff": "0",
            "from_station_code": "HGH",
            "to_station_code": "AOH",
            "seat_price_json": json.dumps(
                [
                    {"code": "O", "name": "二等座", "price": "73.0"},
                    {"code": "M", "name": "一等座", "price": "123.0"},
                ],
                ensure_ascii=False,
            ),
            "stop_count": "2",
            "route_signature": "HGH->AOH",
            "sale_status": "预订",
            "can_web_buy": "Y",
            "seat_inventory_json": "",
        },
    ]
    _write_csv(normalized / "trains.csv", trains_rows)

    stops_rows = [
        {
            "query_date": "2026-03-18",
            "train_no": "24000000G10L",
            "station_train_code": "G1",
            "station_no": "1",
            "station_name": "北京南",
            "arrive_time": "----",
            "start_time": "07:00",
            "running_time": "00:00",
            "arrive_day_diff": "0",
            "is_start": "Y",
            "is_end": "",
        },
        {
            "query_date": "2026-03-18",
            "train_no": "24000000G10L",
            "station_train_code": "G1",
            "station_no": "2",
            "station_name": "济南西",
            "arrive_time": "08:30",
            "start_time": "08:32",
            "running_time": "01:30",
            "arrive_day_diff": "0",
            "is_start": "",
            "is_end": "",
        },
        {
            "query_date": "2026-03-18",
            "train_no": "24000000G10L",
            "station_train_code": "G1",
            "station_no": "3",
            "station_name": "上海虹桥",
            "arrive_time": "11:30",
            "start_time": "11:30",
            "running_time": "04:30",
            "arrive_day_diff": "0",
            "is_start": "",
            "is_end": "Y",
        },
        {
            "query_date": "2026-03-18",
            "train_no": "24000000G20X",
            "station_train_code": "G2",
            "station_no": "1",
            "station_name": "杭州东",
            "arrive_time": "----",
            "start_time": "08:00",
            "running_time": "00:00",
            "arrive_day_diff": "0",
            "is_start": "Y",
            "is_end": "",
        },
        {
            "query_date": "2026-03-18",
            "train_no": "24000000G20X",
            "station_train_code": "G2",
            "station_no": "2",
            "station_name": "上海虹桥",
            "arrive_time": "09:10",
            "start_time": "09:10",
            "running_time": "01:10",
            "arrive_day_diff": "0",
            "is_start": "",
            "is_end": "Y",
        },
    ]
    _write_csv(normalized / "stops.csv", stops_rows)

    routes_rows = [
        {
            "query_date": "2026-03-18",
            "from_station_code": "VNP",
            "to_station_code": "AOH",
            "result_count": "1",
            "fetched_at": "2026-03-12T00:00:00+00:00",
        },
        {
            "query_date": "2026-03-18",
            "from_station_code": "HGH",
            "to_station_code": "AOH",
            "result_count": "1",
            "fetched_at": "2026-03-12T00:00:00+00:00",
        },
    ]
    _write_csv(normalized / "routes.csv", routes_rows)
    return root


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
