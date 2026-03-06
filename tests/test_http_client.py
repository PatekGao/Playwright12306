from playwright12306.http_client import build_default_headers


def test_build_default_headers_contains_referer() -> None:
    headers = build_default_headers(
        "https://kyfw.12306.cn/otn/leftTicket/init?linktypeid=dc"
    )
    assert "Referer" in headers
    assert headers["User-Agent"]
