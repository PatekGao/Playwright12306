from __future__ import annotations

from fastapi.testclient import TestClient

from playwright12306.search_api import create_app
from playwright12306.search_importer import import_artifacts
from tests.search_test_support import write_sample_artifacts_dir


def test_search_api_meta_and_trains_endpoints(tmp_path) -> None:
    artifacts_dir = write_sample_artifacts_dir(tmp_path / "artifacts" / "2026-03-18")
    db_path = tmp_path / "data" / "train_search.db"
    import_artifacts(artifacts_dir=artifacts_dir, db_path=db_path)
    client = TestClient(create_app(db_path))

    summary = client.get("/api/meta/summary")
    assert summary.status_code == 200
    assert summary.json()["query_dates"] == ["2026-03-18"]

    options = client.get("/api/meta/options")
    assert options.status_code == 200
    options_payload = options.json()
    assert "高速" in options_payload["train_classes"]
    assert "上海虹桥" in options_payload["stations"]
    assert "二等座" in options_payload["seat_names"]

    trains = client.get(
        "/api/trains",
        params={
            "query_date": "2026-03-18",
            "start_station_name": "杭州",
            "end_station_name": "上海",
            "seat_name": "二等座",
            "max_price": "100",
            "sort_by": "min_price",
            "sort_order": "asc",
        },
    )
    assert trains.status_code == 200
    payload = trains.json()
    assert payload["total"] == 1
    assert payload["items"][0]["train_code"] == "G2"
    assert payload["items"][0]["min_price"] == 73.0
    assert payload["items"][0]["matched_seat_prices"][0]["seat_name"] == "二等座"
    assert payload["summary"]["total_trains"] == 1
    assert payload["summary"]["matched_prices"] == 1


def test_search_api_supports_interval_search_by_stops(tmp_path) -> None:
    artifacts_dir = write_sample_artifacts_dir(tmp_path / "artifacts" / "2026-03-18")
    db_path = tmp_path / "data" / "train_search.db"
    import_artifacts(artifacts_dir=artifacts_dir, db_path=db_path)
    client = TestClient(create_app(db_path))

    response = client.get(
        "/api/trains",
        params={
            "query_date": "2026-03-18",
            "start_station_name": "济南",
            "end_station_name": "上海",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["train_code"] == "G1"


def test_search_api_detail_and_export_endpoints(tmp_path) -> None:
    artifacts_dir = write_sample_artifacts_dir(tmp_path / "artifacts" / "2026-03-18")
    db_path = tmp_path / "data" / "train_search.db"
    import_artifacts(artifacts_dir=artifacts_dir, db_path=db_path)
    client = TestClient(create_app(db_path))

    detail = client.get("/api/trains/2026-03-18/24000000G10L")
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["train"]["train_code"] == "G1"
    assert len(detail_payload["stops"]) == 3
    assert detail_payload["seat_prices"][0]["seat_name"] in {"二等座", "一等座"}

    exported_csv = client.get(
        "/api/trains/export",
        params={"query_date": "2026-03-18", "format": "csv"},
    )
    assert exported_csv.status_code == 200
    assert exported_csv.content.startswith(b"\xef\xbb\xbf")
    assert "filename*=UTF-8''" in exported_csv.headers["content-disposition"]
    assert "2026-03-18" in exported_csv.headers["content-disposition"]
    assert "train_code" in exported_csv.text
    assert "G1" in exported_csv.text

    exported_json = client.get(
        "/api/trains/export",
        params={"query_date": "2026-03-18", "format": "json", "train_code": "G2"},
    )
    assert exported_json.status_code == 200
    assert exported_json.json()[0]["train_code"] == "G2"


def test_search_api_reports_missing_database(tmp_path) -> None:
    client = TestClient(create_app(tmp_path / "missing.db"))
    response = client.get("/api/meta/summary")
    assert response.status_code == 503
    assert "run import script first" in response.json()["detail"]


def test_search_api_allows_cross_origin_requests(tmp_path) -> None:
    artifacts_dir = write_sample_artifacts_dir(tmp_path / "artifacts" / "2026-03-18")
    db_path = tmp_path / "data" / "train_search.db"
    import_artifacts(artifacts_dir=artifacts_dir, db_path=db_path)
    client = TestClient(create_app(db_path))

    response = client.get(
        "/api/meta/summary",
        headers={"Origin": "https://preview.example.com"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
