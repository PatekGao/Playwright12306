from playwright12306.stations import parse_station_names


def test_parse_station_names_extracts_station_code() -> None:
    raw = "var station_names ='@bji|北京|BJP|beijing|bj|2|0357|北京|||';"
    records = parse_station_names(raw)
    assert records["BJP"].name == "北京"
