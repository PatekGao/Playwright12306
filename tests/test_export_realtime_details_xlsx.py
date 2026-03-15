from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.export_realtime_details_xlsx import export_detail_json_to_xlsx


def test_export_detail_json_to_xlsx_preserves_structured_and_raw_data(tmp_path: Path) -> None:
    payload = {
        "request": {
            "date_from": "2026-03-18",
            "date_to": "2026-03-18",
            "query_mode": "route",
            "query_scope": "city",
            "from_station_name": "上海",
            "to_station_name": "北京",
            "train_code": "",
            "train_class_name": "",
        },
        "daily_results": [
            {
                "query_date": "2026-03-18",
                "summary": {
                    "matched_train_count": 1,
                    "available_train_count": 1,
                    "cheapest_available_price": 553.0,
                    "fastest_duration": "04:18",
                },
                "failure": None,
                "items": [
                    {
                        "query_date": "2026-03-18",
                        "train_no": "240000G1",
                        "train_code": "G1",
                        "train_class_name": "高速",
                        "from_station_name": "上海",
                        "to_station_name": "北京",
                        "matched_from_station_name": "上海虹桥",
                        "matched_to_station_name": "北京南",
                        "depart_time": "07:00",
                        "arrive_time": "11:18",
                        "duration": "04:18",
                        "sale_status": "预订",
                        "can_web_buy": "Y",
                        "route_signature": "SHH->BJP",
                        "matched_route_signature": "AOH->VNP",
                        "min_price": 553.0,
                        "seat_offers": [
                            {
                                "seat_code": "O",
                                "seat_name": "二等座",
                                "price": 553.0,
                                "inventory_text": "有",
                                "is_available": True,
                            }
                        ],
                    }
                ],
            }
        ],
        "aggregated_results": [
            {
                "train_code": "G1",
                "available_days": 1,
                "min_price": 553.0,
            }
        ],
        "partial_failures": [
            {
                "query_date": "2026-03-19",
                "stage": "querying_date",
                "error_type": "upstream_error",
                "message": "timeout",
            }
        ],
        "summary": {
            "total_days": 2,
            "successful_days": 1,
            "failed_days": 1,
            "available_train_count": 1,
            "cheapest_available_price": 553.0,
            "fastest_duration": "04:18",
            "matched_train_count": 1,
        },
    }
    input_json = tmp_path / "detail.json"
    input_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    output_path = export_detail_json_to_xlsx(input_json, tmp_path / "xlsx")

    overview = pd.read_excel(output_path, sheet_name="overview")
    items = pd.read_excel(output_path, sheet_name="daily_items")
    offers = pd.read_excel(output_path, sheet_name="seat_offers")
    tree = pd.read_excel(output_path, sheet_name="json_tree")
    raw_json = pd.read_excel(output_path, sheet_name="raw_json")

    assert output_path.exists()
    assert overview.loc[0, "from_station_name"] == "上海"
    assert overview.loc[0, "partial_failure_count"] == 1
    assert items.loc[0, "train_code"] == "G1"
    assert offers.loc[0, "seat_name"] == "二等座"
    assert "root.daily_results[0].items[0].seat_offers[0].seat_name" in tree["path"].tolist()
    assert raw_json.loc[0, "line_number"] == 1
