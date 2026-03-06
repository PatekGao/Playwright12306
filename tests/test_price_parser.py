from playwright12306.price_parser import build_seat_price_items, parse_info_all_list


def test_parse_info_all_list_extracts_second_class_price() -> None:
    prices = parse_info_all_list("O066903000#M107000000")
    assert prices["O"] == "669.0"
    assert prices["M"] == "1070.0"


def test_parse_info_all_list_supports_fixed_width_encoding() -> None:
    prices = parse_info_all_list("302835000040455500001015650000")
    assert prices["3"] == "283.5"
    assert prices["4"] == "455.5"
    assert prices["1"] == "156.5"


def test_build_seat_price_items_adds_human_readable_names() -> None:
    items = build_seat_price_items({"O": "669.0", "M": "1070.0"})
    assert items[0]["name"] == "二等座"
    assert items[1]["name"] == "一等座"
