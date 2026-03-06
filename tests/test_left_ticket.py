from playwright12306.left_ticket import parse_left_ticket_row


def test_parse_left_ticket_row_extracts_basic_fields() -> None:
    row = (
        "|预订|24000000G520|G5|BJP|SHH|BJP|SHH|21:21|09:27|12:06|Y|"
        "||||||||||有|||||有||有||||J0O0I0|JOI|0|0||J054200021O036100021I068600021|"
        "0|||||1|0#1#0#0#z#0#JI#z|||CHN,CHN|||N#N#|||202603061000|Y|"
    )
    parsed = parse_left_ticket_row(row)
    assert parsed.train_no == "24000000G520"
    assert parsed.station_train_code == "G5"
    assert parsed.from_station_code == "BJP"
