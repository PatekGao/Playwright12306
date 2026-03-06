from playwright12306.train_info import parse_train_info


def test_parse_train_info_extracts_stops() -> None:
    payload = {
        "status": True,
        "data": {
            "data": [
                {
                    "station_name": "北京",
                    "station_train_code": "1461",
                    "start_station_name": "北京",
                    "end_station_name": "上海",
                    "station_no": "01",
                    "arrive_time": "----",
                    "start_time": "11:59",
                    "running_time": "00:00",
                    "arrive_day_diff": "0",
                    "is_start": "Y",
                }
            ]
        },
    }
    result = parse_train_info(payload, query_date="2026-03-20", train_no="240000146135")
    assert result.summary.start_station_name == "北京"
    assert result.summary.depart_time == "11:59"
    assert len(result.stops) == 1


def test_parse_train_info_derives_end_flag_for_last_stop() -> None:
    payload = {
        "status": True,
        "data": {
            "data": [
                {
                    "station_name": "北京",
                    "station_train_code": "1461",
                    "start_station_name": "北京",
                    "end_station_name": "上海",
                    "station_no": "01",
                    "arrive_time": "----",
                    "start_time": "11:59",
                    "running_time": "00:00",
                    "arrive_day_diff": "0",
                    "is_start": "Y",
                },
                {
                    "station_name": "上海",
                    "station_train_code": "1461",
                    "station_no": "02",
                    "arrive_time": "06:45",
                    "start_time": "06:45",
                    "running_time": "18:46",
                    "arrive_day_diff": "1",
                },
            ]
        },
    }
    result = parse_train_info(payload, query_date="2026-03-20", train_no="240000146135")
    assert result.stops[0].is_start == "Y"
    assert result.stops[-1].is_end == "Y"
