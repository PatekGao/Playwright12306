"""Price parsing helpers derived from the 12306 public ticket page."""

from __future__ import annotations

SEAT_NAME_MAP = {
    "A": "高级动卧",
    "B": "混编硬座",
    "C": "混编硬卧",
    "D": "优选一等座",
    "E": "特等软座",
    "F": "动卧",
    "F1": "下铺",
    "F3": "上铺",
    "G": "二人软包",
    "H": "一人软包",
    "H1": "下铺",
    "H3": "上铺",
    "I": "一等卧",
    "I1": "下铺",
    "I3": "上铺",
    "J": "二等卧",
    "J1": "下铺",
    "J2": "中铺",
    "J3": "上铺",
    "K": "混编软座",
    "L": "混编软卧",
    "M": "一等座",
    "O": "二等座",
    "P": "特等座",
    "Q": "多功能座",
    "S": "二等包座",
    "0": "棚车",
    "1": "硬座",
    "2": "软座",
    "3": "硬卧",
    "31": "下铺",
    "32": "中铺",
    "33": "上铺",
    "4": "软卧",
    "41": "下铺",
    "43": "上铺",
    "5": "包厢硬卧",
    "6": "高级软卧",
    "61": "下铺",
    "63": "上铺",
    "7": "一等软座",
    "8": "二等软座",
    "9": "商务座",
    "W": "无座",
}


def _format_price(value: float) -> str:
    """Format a numeric price with one decimal place."""

    return f"{value:.1f}"


def _iter_price_chunks(raw: str) -> list[str]:
    """Split a raw 12306 price string into 10-char chunks.

    The endpoint currently returns two encodings in the wild:
    - hash-delimited chunks, e.g. ``O066903000#M107000000``
    - fixed-width concatenated chunks, e.g. ``302835000040455500001015650000``
    """

    if "#" in raw:
        return [chunk for chunk in raw.split("#") if chunk]
    return [raw[index : index + 10] for index in range(0, len(raw), 10)]


def parse_info_all_list(raw: str) -> dict[str, str]:
    """Parse the `infoAll_list` field into structured prices.

    Args:
        raw: Hash-delimited seat price encoding from `leftTicket/queryG`.

    Returns:
        A mapping from seat code to decimal price string.
    """

    prices: dict[str, str] = {}
    if not raw:
        return prices

    for chunk in _iter_price_chunks(raw):
        if len(chunk) < 10:
            continue
        seat_code = chunk[0]
        sub_code = "" if chunk[9] == "0" else chunk[9]
        price = _format_price(int(chunk[1:6]) / 10)
        prices[f"{seat_code}{sub_code}"] = price
        if sub_code:
            prices[seat_code] = price
        elif seat_code not in prices:
            prices[seat_code] = price
    return prices


def build_seat_price_items(prices: dict[str, str]) -> list[dict[str, str]]:
    """Convert a parsed price mapping into user-facing seat items."""

    items: list[dict[str, str]] = []
    for seat_code, price in prices.items():
        items.append(
            {
                "code": seat_code,
                "name": SEAT_NAME_MAP.get(seat_code, seat_code),
                "price": price,
            }
        )
    return items
