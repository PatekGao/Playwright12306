"""CLI for realtime 12306 route and station queries."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from playwright12306.realtime import (
    RealtimeQueryError,
    RealtimeQueryService,
    normalize_realtime_request,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the realtime CLI parser."""

    parser = argparse.ArgumentParser(description="Query 12306 realtime tickets and schedules.")
    parser.add_argument("--date", default=None, help="Single query date in YYYY-MM-DD format.")
    parser.add_argument("--date-from", default=None, help="Start date in YYYY-MM-DD format.")
    parser.add_argument("--date-to", default=None, help="End date in YYYY-MM-DD format.")
    parser.add_argument("--from-station", default="", help="Departure station name.")
    parser.add_argument("--to-station", default="", help="Arrival station name.")
    parser.add_argument(
        "--query-scope",
        choices=["station", "city"],
        default="station",
        help="Interpret input names as exact stations or city-level groups.",
    )
    parser.add_argument("--train-code", default="", help="Exact train code, e.g. G5.")
    parser.add_argument("--train-class", default="", help="Train class filter, e.g. 高速 / 动车.")
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format.",
    )
    parser.add_argument(
        "--detail",
        action="store_true",
        help="Print seat offers or matched station details for each result row.",
    )
    parser.add_argument("--output", default="", help="Optional output file path.")
    return parser


def format_progress(event: dict[str, object]) -> str:
    """Format one progress event for terminal output."""

    parts = [f"[{event.get('event', 'progress')}]"]
    if event.get("query_date"):
        parts.append(str(event["query_date"]))
    if event.get("message"):
        parts.append(str(event["message"]))
    if event.get("train_code"):
        parts.append(str(event["train_code"]))
    return " ".join(parts)


def render_text_result(result: dict[str, object], detail: bool) -> str:
    """Render one realtime result as plain text."""

    lines: list[str] = []
    request = result["request"]
    lines.append(
        f"mode={request['query_mode']} scope={request['query_scope']} date={request['date_from']}..{request['date_to']}"
    )
    lines.append(
        f"matched={result['summary']['matched_train_count']} failed_days={result['summary']['failed_days']}"
    )
    if request["query_mode"] == "single_head":
        lines.append("提示: 单头模式不返回票价和余票。")
    for daily in result["daily_results"]:
        lines.append(f"\n[{daily['query_date']}] matched={daily['summary']['matched_train_count']}")
        for item in daily["items"]:
            base = (
                f"{item['train_code']} {item['start_station_name']}->{item['end_station_name']} "
                f"{item['depart_time']}-{item['arrive_time']} {item['duration']}"
            )
            if item["route_signature"]:
                base += f" {item['route_signature']}"
            if item.get("min_price") is not None:
                base += f" min=¥{item['min_price']:.1f}"
            lines.append(base)
            if detail:
                if item["seat_offers"]:
                    for seat in item["seat_offers"]:
                        price_text = (
                            f"¥{seat['price']:.1f}" if seat.get("price") is not None else "--"
                        )
                        lines.append(
                            f"  - {seat['seat_name']}: {price_text} / {seat['inventory_text'] or '--'}"
                        )
                elif item.get("matched_station_name"):
                    lines.append(
                        "  - "
                        f"{item['matched_station_name']} 到 {item['matched_arrive_time']} 发 {item['matched_depart_time']}"
                    )
    if result["partial_failures"]:
        lines.append("\npartial_failures:")
        for failure in result["partial_failures"]:
            lines.append(
                f"- {failure['query_date']} {failure['error_type']} {failure['message']}"
            )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the realtime CLI."""

    args = build_parser().parse_args(argv)
    payload = {
        "date": args.date,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "from_station_name": args.from_station,
        "to_station_name": args.to_station,
        "query_scope": args.query_scope,
        "train_code": args.train_code,
        "train_class_name": args.train_class,
    }
    try:
        request = normalize_realtime_request(payload)
    except RealtimeQueryError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    service = RealtimeQueryService()
    try:
        result = service.run_query(request, progress_callback=lambda event: print(format_progress(event)))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.format == "json":
        rendered = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        rendered = render_text_result(result, args.detail)
    if args.output:
        Path(args.output).expanduser().write_text(rendered, encoding="utf-8")
        print(args.output)
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
