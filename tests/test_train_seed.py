from playwright12306.train_seed import parse_train_seed


def test_parse_train_seed_extracts_train_no() -> None:
    payload = {
        "status": True,
        "data": [
            {"station_train_code": "G1(北京南-上海虹桥)", "train_no": "24000000G10L"}
        ],
    }
    rows = parse_train_seed(payload, query_date="2026-03-20")
    assert rows[0].train_no == "24000000G10L"


def test_parse_train_seed_deduplicates_same_train() -> None:
    payload = {
        "status": True,
        "data": [
            {"station_train_code": "1461(北京-上海)", "train_no": "240000146135"},
            {"station_train_code": "1461(北京-上海)", "train_no": "240000146135"},
        ],
    }
    rows = parse_train_seed(payload, query_date="2026-03-20")
    assert len(rows) == 1
