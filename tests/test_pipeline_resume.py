import json

from playwright12306.left_ticket import LeftTicketRow
from playwright12306.pipeline import build_train_output_row, should_skip_done_item
from playwright12306.train_info import TrainSummary


def test_should_skip_done_item() -> None:
    done = {"24000000G10L"}
    assert should_skip_done_item("24000000G10L", done) is True
    assert should_skip_done_item("24000000G520", done) is False


def test_build_train_output_row_includes_structured_prices() -> None:
    summary = TrainSummary(
        query_date="2026-03-20",
        train_no="24000000G520",
        station_train_code="G5",
        train_class_name="高速",
        start_station_name="北京",
        end_station_name="上海",
        depart_time="21:21",
        arrive_time="09:27",
        duration="12:06",
        arrive_day_diff="1",
    )
    price_source = LeftTicketRow(
        raw_row="raw",
        train_no="24000000G520",
        station_train_code="G5",
        from_station_code="BJP",
        to_station_code="SHH",
        start_station_code="BJP",
        end_station_code="SHH",
        depart_time="21:21",
        arrive_time="09:27",
        duration="12:06",
        can_web_buy="Y",
        yp_info_new="O066903000#M107000000",
        seat_types="OM",
    )
    row = build_train_output_row(summary=summary, price_source=price_source)
    prices = json.loads(row["seat_price_json"])
    assert row["train_no"] == "24000000G520"
    assert prices[0]["name"] == "二等座"
