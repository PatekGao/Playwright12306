from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from playwright12306.realtime import (
    RealtimeJobManager,
    RealtimeQueryService,
    choose_city_anchor_station,
    normalize_realtime_request,
)
from playwright12306.search_api import create_app
from playwright12306.stations import StationRecord


def _build_left_ticket_row(
    *,
    train_no: str,
    train_code: str,
    start_code: str,
    end_code: str,
    from_code: str,
    to_code: str,
    depart_time: str,
    arrive_time: str,
    duration: str,
    sale_status: str,
    can_web_buy: str,
    yp_info_new: str,
    second_class: str = "",
    first_class: str = "",
    business_class: str = "",
    no_seat: str = "",
) -> str:
    parts = [""] * 46
    parts[1] = sale_status
    parts[2] = train_no
    parts[3] = train_code
    parts[4] = start_code
    parts[5] = end_code
    parts[6] = from_code
    parts[7] = to_code
    parts[8] = depart_time
    parts[9] = arrive_time
    parts[10] = duration
    parts[11] = can_web_buy
    parts[26] = no_seat
    parts[30] = second_class
    parts[31] = first_class
    parts[32] = business_class
    parts[35] = "OM9W"
    parts[39] = yp_info_new
    return "|".join(parts)


def build_fake_service() -> RealtimeQueryService:
    station_map = {
        "VNP": StationRecord(name="北京南", telecode="VNP"),
        "JNK": StationRecord(name="济南西", telecode="JNK"),
        "HZH": StationRecord(name="杭州", telecode="HZH"),
        "HGH": StationRecord(name="杭州东", telecode="HGH"),
        "AOH": StationRecord(name="上海虹桥", telecode="AOH"),
        "IMH": StationRecord(name="上海松江", telecode="IMH"),
    }

    route_payloads = {
        ("2026-03-18", "HGH", "AOH"): {
            "data": {
                "result": [
                    _build_left_ticket_row(
                        train_no="24000000G20X",
                        train_code="G2",
                        start_code="HGH",
                        end_code="AOH",
                        from_code="HZH",
                        to_code="IMH",
                        depart_time="08:00",
                        arrive_time="09:10",
                        duration="01:10",
                        sale_status="预订",
                        can_web_buy="Y",
                        yp_info_new="O000730000#M001230000#9002450000",
                        second_class="有",
                        first_class="5",
                        business_class="2",
                        no_seat="无",
                    ),
                ],
                "map": {"HZH": "杭州", "IMH": "上海松江", "HGH": "杭州东", "AOH": "上海虹桥"},
            }
        },
        ("2026-03-18", "HZH", "AOH"): {"data": {"result": [], "map": {"HZH": "杭州", "AOH": "上海虹桥"}}},
        ("2026-03-18", "HZH", "IMH"): {"data": {"result": [], "map": {"HZH": "杭州", "IMH": "上海松江"}}},
        ("2026-03-18", "HGH", "IMH"): {"data": {"result": [], "map": {"HGH": "杭州东", "IMH": "上海松江"}}},
        ("2026-03-19", "HGH", "AOH"): {
            "data": {
                "result": [
                    _build_left_ticket_row(
                        train_no="24000000G20X",
                        train_code="G2",
                        start_code="HGH",
                        end_code="AOH",
                        from_code="HZH",
                        to_code="IMH",
                        depart_time="08:00",
                        arrive_time="09:10",
                        duration="01:10",
                        sale_status="预订",
                        can_web_buy="Y",
                        yp_info_new="O000760000#M001260000",
                        second_class="无",
                        first_class="无",
                        business_class="无",
                    ),
                ],
                "map": {"HZH": "杭州", "IMH": "上海松江", "HGH": "杭州东", "AOH": "上海虹桥"},
            }
        },
        ("2026-03-19", "HZH", "AOH"): {"data": {"result": [], "map": {"HZH": "杭州", "AOH": "上海虹桥"}}},
        ("2026-03-19", "HZH", "IMH"): {"data": {"result": [], "map": {"HZH": "杭州", "IMH": "上海松江"}}},
        ("2026-03-19", "HGH", "IMH"): {"data": {"result": [], "map": {"HGH": "杭州东", "IMH": "上海松江"}}},
    }

    train_seed_payloads = {
        "2026-03-18": {
            "data": [
                {"station_train_code": "G1", "train_no": "24000000G10L"},
                {"station_train_code": "G2", "train_no": "24000000G20X"},
            ]
        }
    }
    train_info_payloads = {
        ("2026-03-18", "24000000G10L"): {
            "data": {
                "data": [
                    {
                        "station_train_code": "G1",
                        "train_class_name": "高速",
                        "start_station_name": "北京南",
                        "end_station_name": "上海虹桥",
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
                        "station_train_code": "G1",
                        "train_class_name": "高速",
                        "start_station_name": "北京南",
                        "end_station_name": "上海虹桥",
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
                        "station_train_code": "G1",
                        "train_class_name": "高速",
                        "start_station_name": "北京南",
                        "end_station_name": "上海虹桥",
                        "station_no": "3",
                        "station_name": "上海虹桥",
                        "arrive_time": "11:30",
                        "start_time": "11:30",
                        "running_time": "04:30",
                        "arrive_day_diff": "0",
                        "is_start": "",
                        "is_end": "Y",
                    },
                ]
            }
        },
        ("2026-03-18", "24000000G20X"): {
            "data": {
                "data": [
                    {
                        "station_train_code": "G2",
                        "train_class_name": "高速",
                        "start_station_name": "杭州东",
                        "end_station_name": "上海虹桥",
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
                        "station_train_code": "G2",
                        "train_class_name": "高速",
                        "start_station_name": "杭州东",
                        "end_station_name": "上海虹桥",
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
            }
        },
    }

    return RealtimeQueryService(
        station_fetcher=lambda session: station_map,
        train_seed_fetcher=lambda session, query_date: train_seed_payloads[query_date],
        train_info_fetcher=lambda session, query_date, train_no: train_info_payloads[(query_date, train_no)],
        left_ticket_bootstrapper=lambda session: None,
        left_ticket_fetcher=lambda session, query_date, from_code, to_code: route_payloads[
            (query_date, from_code, to_code)
        ],
    )


def test_choose_city_anchor_station_prefers_city_core_name() -> None:
    station_name_index = {"上海": "SHH", "上海虹桥": "AOH", "上海松江": "IMH"}
    city_name_index = {
        "上海": [
            StationRecord(name="上海虹桥", telecode="AOH"),
            StationRecord(name="上海", telecode="SHH"),
            StationRecord(name="上海松江", telecode="IMH"),
        ]
    }

    anchor = choose_city_anchor_station(
        "上海",
        station_name_index=station_name_index,
        city_name_index=city_name_index,
    )

    assert anchor.name == "上海"
    assert anchor.telecode == "SHH"


def test_realtime_route_query_station_scope_keeps_exact_station_matches_only() -> None:
    service = build_fake_service()
    request = normalize_realtime_request(
        {
            "date": "2026-03-18",
            "from_station_name": "杭州东",
            "to_station_name": "上海虹桥",
            "query_mode": "route",
            "query_scope": "station",
        }
    )

    result = service.run_query(request)

    assert result["summary"]["successful_days"] == 1
    assert result["summary"]["matched_train_count"] == 0
    assert result["daily_results"][0]["items"] == []


def test_realtime_route_query_city_scope_returns_city_level_matches() -> None:
    service = build_fake_service()
    request = normalize_realtime_request(
        {
            "date_from": "2026-03-18",
            "date_to": "2026-03-19",
            "from_station_name": "杭州东",
            "to_station_name": "上海虹桥",
            "query_mode": "route",
            "query_scope": "city",
        }
    )

    result = service.run_query(request)

    assert result["summary"]["successful_days"] == 2
    assert result["summary"]["matched_train_count"] == 1
    assert result["request"]["query_scope"] == "city"
    assert result["daily_results"][0]["items"][0]["from_station_name"] == "杭州东"
    assert result["daily_results"][0]["items"][0]["to_station_name"] == "上海虹桥"
    assert result["daily_results"][0]["items"][0]["matched_from_station_name"] == "杭州"
    assert result["daily_results"][0]["items"][0]["matched_to_station_name"] == "上海松江"
    assert result["daily_results"][0]["items"][0]["seat_offers"][0]["seat_name"] == "二等座"
    assert result["daily_results"][0]["items"][0]["seat_offers"][0]["inventory_text"] == "有"
    assert result["aggregated_results"][0]["available_days"] == 1
    assert result["aggregated_results"][0]["sold_out_days"] == 1


def test_realtime_single_head_query_returns_schedule_only() -> None:
    service = build_fake_service()
    request = normalize_realtime_request(
        {
            "date": "2026-03-18",
            "from_station_name": "济南西",
            "query_mode": "single_head",
        }
    )

    result = service.run_query(request)

    assert result["summary"]["matched_train_count"] == 1
    item = result["daily_results"][0]["items"][0]
    assert item["train_code"] == "G1"
    assert item["matched_station_name"] == "济南西"
    assert item["seat_offers"] == []
    assert item["sale_status"] == ""


def test_realtime_api_job_flow_and_detail_endpoint(tmp_path) -> None:
    service = build_fake_service()
    app = create_app(
        tmp_path / "missing.db",
        realtime_service=service,
        realtime_manager=RealtimeJobManager(service),
        web_dist=tmp_path / "missing-dist",
    )
    client = TestClient(app)

    stations = client.get("/api/realtime/meta/stations")
    assert stations.status_code == 200
    assert "杭州东" in stations.json()["stations"]
    assert "杭州" in stations.json()["cities"]

    created = client.post(
        "/api/realtime/jobs",
        json={
            "date": "2026-03-18",
            "from_station_name": "杭州东",
            "to_station_name": "上海虹桥",
            "query_scope": "city",
        },
    )
    assert created.status_code == 200
    job_id = created.json()["job_id"]

    for _ in range(20):
        payload = client.get(f"/api/realtime/jobs/{job_id}").json()
        if payload["status"] == "completed":
            break
    assert payload["status"] == "completed"
    assert payload["result"]["daily_results"][0]["items"][0]["train_code"] == "G2"

    events = client.get(f"/api/realtime/jobs/{job_id}/events")
    assert events.status_code == 200
    assert "event: queued" in events.text
    assert "event: completed" in events.text

    exported = client.get(f"/api/realtime/jobs/{job_id}/export", params={"format": "csv"})
    assert exported.status_code == 200
    assert exported.content.startswith(b"\xef\xbb\xbf")
    assert "filename*=UTF-8''" in exported.headers["content-disposition"]
    assert "2026-03-18" in exported.headers["content-disposition"]
    assert "train_code" in exported.text
    assert "G2" in exported.text

    detail = client.get(
        "/api/realtime/trains/2026-03-18/24000000G20X",
        params={"from_station_name": "杭州东", "to_station_name": "上海虹桥"},
    )
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["train"]["train_code"] == "G2"
    assert detail_payload["train"]["from_station_name"] == "杭州东"
    assert detail_payload["train"]["to_station_name"] == "上海虹桥"
    assert detail_payload["seat_offers"][0]["seat_name"] == "二等座"


def test_realtime_api_rejects_invalid_range(tmp_path) -> None:
    service = build_fake_service()
    app = create_app(
        Path(tmp_path / "missing.db"),
        realtime_service=service,
        realtime_manager=RealtimeJobManager(service),
        web_dist=tmp_path / "missing-dist",
    )
    client = TestClient(app)

    response = client.post(
        "/api/realtime/jobs",
        json={
            "date_from": "2026-03-18",
            "date_to": "2026-03-26",
            "from_station_name": "杭州东",
            "to_station_name": "上海虹桥",
        },
    )

    assert response.status_code == 422
    assert "cannot exceed" in response.json()["detail"]
