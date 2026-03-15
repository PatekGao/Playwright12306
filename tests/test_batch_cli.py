from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.batch_query_realtime_tickets import (
    build_template_dataframe,
    run_batch_queries,
    write_example_workbook,
)


class FakeRealtimeService:
    def run_query(self, request):
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
            "daily_results": [],
            "aggregated_results": [],
            "partial_failures": [],
            "summary": {
                "total_days": 1,
                "successful_days": 1,
                "failed_days": 0,
                "available_train_count": 2,
                "cheapest_available_price": 123.4,
                "fastest_duration": "01:30",
                "matched_train_count": 3,
            },
        }


def test_write_example_workbook_creates_queries_sheet(tmp_path: Path) -> None:
    target = tmp_path / "example.xlsx"
    write_example_workbook(target)

    dataframe = pd.read_excel(target, sheet_name="queries")

    assert list(dataframe.columns) == list(build_template_dataframe().columns)
    assert len(dataframe) == 3


def test_run_batch_queries_writes_summary_and_detail_files(tmp_path: Path) -> None:
    input_path = tmp_path / "input.xlsx"
    rows = pd.DataFrame(
        [
            {
                "enabled": "Y",
                "date": "2026-03-18",
                "query_scope": "city",
                "from_station_name": "上海",
                "to_station_name": "北京",
                "note": "ok",
            },
            {
                "enabled": "N",
                "date": "2026-03-18",
                "query_scope": "city",
                "from_station_name": "杭州",
                "to_station_name": "上海",
                "note": "skip",
            },
            {
                "enabled": "maybe",
                "date": "2026-03-18",
                "query_scope": "city",
                "from_station_name": "广州",
                "to_station_name": "深圳",
                "note": "bad-enabled",
            },
        ]
    )
    with pd.ExcelWriter(input_path) as writer:
        rows.to_excel(writer, index=False, sheet_name="queries")

    result = run_batch_queries(
        input_path,
        output_dir=tmp_path / "out",
        service=FakeRealtimeService(),
    )

    summary = pd.read_csv(result.summary_csv)
    detail_files = list(result.details_dir.glob("*.json"))

    assert result.total_rows == 3
    assert result.executed_rows == 1
    assert result.succeeded_rows == 1
    assert result.failed_rows == 1
    assert result.skipped_rows == 1
    assert result.summary_xlsx.exists()
    assert len(detail_files) == 1
    assert summary["status"].tolist() == ["completed", "skipped", "failed"]

    payload = json.loads(detail_files[0].read_text(encoding="utf-8"))
    assert payload["request"]["from_station_name"] == "上海"
    assert payload["summary"]["matched_train_count"] == 3
