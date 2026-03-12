"""Fetch pipeline orchestration for nationwide 12306 train data."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from playwright12306.config import AppConfig
from playwright12306.http_client import create_session
from playwright12306.left_ticket import (
    LeftTicketRow,
    bootstrap_left_ticket_session,
    fetch_left_ticket_payload,
    parse_left_ticket_payload,
)
from playwright12306.models import to_serializable_dict
from playwright12306.price_parser import build_seat_price_items, parse_info_all_list
from playwright12306.stations import build_station_name_index, fetch_station_map
from playwright12306.storage import (
    append_done_key,
    append_jsonl,
    load_done_keys,
    read_json,
    write_csv,
    write_json,
    write_jsonl,
)
from playwright12306.train_info import (
    TrainInfoResult,
    TrainSummary,
    fetch_train_info_payload,
    parse_train_info,
)
from playwright12306.train_seed import TrainSeed, fetch_train_seed_payload, parse_train_seed

TRAIN_TYPE_MAP = {
    "G": "G-高铁",
    "C": "C-城际",
    "D": "D-动车",
    "Z": "Z-直达",
    "T": "T-特快",
    "K": "K-快速",
    "O": "其他",
}


@dataclass(frozen=True)
class PipelineResult:
    """Summary of one pipeline execution."""

    train_count: int
    stop_count: int
    route_count: int
    trains_csv: Path
    stops_csv: Path
    routes_csv: Path


def should_skip_done_item(key: str, done: set[str]) -> bool:
    """Return whether a work item has already been completed."""

    return key in done


def format_progress_message(stage: str, current: int, total: int, detail: str = "") -> str:
    """Format one human-readable progress message."""

    suffix = f" {detail}" if detail else ""
    return f"[progress] {stage} {current}/{total}{suffix}"


def build_train_output_row(
    *,
    summary: TrainSummary,
    price_source: LeftTicketRow | None,
    from_station_code: str = "",
    to_station_code: str = "",
) -> dict[str, str]:
    """Build one normalized train row."""

    effective_from = price_source.from_station_code if price_source else from_station_code
    effective_to = price_source.to_station_code if price_source else to_station_code
    effective_prices = (
        build_seat_price_items(parse_info_all_list(price_source.yp_info_new))
        if price_source and price_source.yp_info_new
        else []
    )
    train_type = TRAIN_TYPE_MAP.get(summary.station_train_code[:1], "其他")
    return {
        "query_date": summary.query_date,
        "train_no": summary.train_no,
        "train_code": summary.station_train_code,
        "station_train_code": summary.station_train_code,
        "train_class_name": summary.train_class_name or train_type,
        "start_station_name": summary.start_station_name,
        "end_station_name": summary.end_station_name,
        "from_station_name": summary.start_station_name,
        "to_station_name": summary.end_station_name,
        "depart_time": summary.depart_time,
        "arrive_time": summary.arrive_time,
        "duration": summary.duration,
        "arrive_day_diff": summary.arrive_day_diff,
        "from_station_code": effective_from,
        "to_station_code": effective_to,
        "seat_price_json": json.dumps(effective_prices, ensure_ascii=False),
        "stop_count": "",
        "route_signature": f"{effective_from}->{effective_to}" if effective_from and effective_to else "",
        "sale_status": price_source.sale_status if price_source else "",
        "can_web_buy": price_source.can_web_buy if price_source else "",
        "seat_inventory_json": "",
    }


class NationwideTrainPipeline:
    """End-to-end pipeline for nationwide train schedules and prices."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.session = create_session()

    def run(self) -> PipelineResult:
        """Execute the full pipeline and write normalized outputs."""

        station_map = fetch_station_map(
            self.session,
            timeout_seconds=self.config.timeout_seconds,
        )
        station_name_index = build_station_name_index(station_map)

        seeds_payload = fetch_train_seed_payload(
            self.session,
            self.config.query_date,
            timeout_seconds=self.config.timeout_seconds,
        )
        append_jsonl(
            self.config.paths.get_train_name_raw,
            self._wrap_raw_record(
                endpoint="queryTrainInfo/getTrainName",
                request_params={"date": self.config.query_date},
                response_body=seeds_payload,
            ),
        )
        seeds = parse_train_seed(seeds_payload, self.config.query_date)
        if self.config.limit_trains is not None:
            seeds = seeds[: self.config.limit_trains]
        self._emit_progress("train_seed", len(seeds), len(seeds), f"query_date={self.config.query_date}")

        schedule_results = self._collect_train_info(seeds)
        summaries = [item.summary for item in schedule_results]
        stops = [stop for item in schedule_results for stop in item.stops]
        price_sources, route_rows = self._collect_price_sources(summaries, station_name_index)

        stop_counts = {
            summary.train_no: sum(1 for stop in stops if stop.train_no == summary.train_no)
            for summary in summaries
        }
        train_rows = []
        for summary in summaries:
            from_code = station_name_index.get(summary.start_station_name, "")
            to_code = station_name_index.get(summary.end_station_name, "")
            row = build_train_output_row(
                summary=summary,
                price_source=price_sources.get(summary.train_no),
                from_station_code=from_code,
                to_station_code=to_code,
            )
            row["stop_count"] = str(stop_counts.get(summary.train_no, 0))
            train_rows.append(row)

        stop_rows = [to_serializable_dict(stop) for stop in stops]
        write_csv(self.config.paths.trains_csv, train_rows)
        write_jsonl(self.config.paths.trains_jsonl, train_rows)
        write_csv(self.config.paths.stops_csv, stop_rows)
        write_csv(self.config.paths.routes_csv, route_rows)

        return PipelineResult(
            train_count=len(train_rows),
            stop_count=len(stop_rows),
            route_count=len(route_rows),
            trains_csv=self.config.paths.trains_csv,
            stops_csv=self.config.paths.stops_csv,
            routes_csv=self.config.paths.routes_csv,
        )

    def _collect_train_info(self, seeds: list[TrainSeed]) -> list[TrainInfoResult]:
        done = set() if self.config.force else load_done_keys(self.config.paths.train_info_done)
        results: list[TrainInfoResult] = []
        total = len(seeds)
        for index, seed in enumerate(seeds, start=1):
            self._emit_progress("train_info", index, total, seed.station_train_code)
            raw_path = self.config.paths.train_info_raw / f"{seed.train_no}.json"
            payload: dict | None = None
            if should_skip_done_item(seed.train_no, done) and raw_path.exists():
                payload = read_json(raw_path)["response_body"]
            else:
                try:
                    payload = fetch_train_info_payload(
                        self.session,
                        self.config.query_date,
                        seed.train_no,
                        timeout_seconds=self.config.timeout_seconds,
                    )
                except Exception as exc:
                    self._log_error("queryTrainInfo/query", {"train_no": seed.train_no}, str(exc))
                    continue
                write_json(
                    raw_path,
                    self._wrap_raw_record(
                        endpoint="queryTrainInfo/query",
                        request_params={
                            "leftTicketDTO.train_no": seed.train_no,
                            "leftTicketDTO.train_date": self.config.query_date,
                        },
                        response_body=payload,
                    ),
                )
                append_done_key(self.config.paths.train_info_done, seed.train_no)
            try:
                results.append(parse_train_info(payload, self.config.query_date, seed.train_no))
            except Exception as exc:
                self._log_error("parse_train_info", {"train_no": seed.train_no}, str(exc))
        return results

    def _collect_price_sources(
        self,
        summaries: list[TrainSummary],
        station_name_index: dict[str, str],
    ) -> tuple[dict[str, LeftTicketRow], list[dict[str, str]]]:
        route_rows: list[dict[str, str]] = []
        price_sources: dict[str, LeftTicketRow] = {}
        done = set() if self.config.force else load_done_keys(self.config.paths.left_ticket_done)
        route_cache: dict[str, dict[str, LeftTicketRow]] = {}
        if not summaries:
            return price_sources, route_rows
        route_total = len(self._build_unique_route_keys(summaries, station_name_index))
        route_index = 0

        try:
            bootstrap_left_ticket_session(
                self.session,
                timeout_seconds=self.config.timeout_seconds,
            )
        except Exception as exc:
            self._log_error("leftTicket/init", {}, str(exc))
            return price_sources, route_rows

        for summary in summaries:
            from_code = station_name_index.get(summary.start_station_name, "")
            to_code = station_name_index.get(summary.end_station_name, "")
            if not from_code or not to_code:
                self._log_error(
                    "station_lookup",
                    {"train_no": summary.train_no},
                    "missing start or end station telecode",
                )
                continue

            route_key = f"{from_code}_{to_code}"
            if route_key not in route_cache:
                route_index += 1
                self._emit_progress("left_ticket", route_index, route_total, route_key)
                raw_path = self.config.paths.left_ticket_raw / f"{route_key}.json"
                payload: dict | None = None
                if should_skip_done_item(route_key, done) and raw_path.exists():
                    payload = read_json(raw_path)["response_body"]
                else:
                    try:
                        payload = fetch_left_ticket_payload(
                            self.session,
                            self.config.query_date,
                            from_code,
                            to_code,
                            timeout_seconds=self.config.timeout_seconds,
                        )
                    except Exception as exc:
                        self._log_error(
                            "leftTicket/queryG",
                            {"from_station": from_code, "to_station": to_code},
                            str(exc),
                        )
                        continue
                    write_json(
                        raw_path,
                        self._wrap_raw_record(
                            endpoint="leftTicket/queryG",
                            request_params={
                                "leftTicketDTO.train_date": self.config.query_date,
                                "leftTicketDTO.from_station": from_code,
                                "leftTicketDTO.to_station": to_code,
                                "purpose_codes": "ADULT",
                            },
                            response_body=payload,
                        ),
                    )
                    append_done_key(self.config.paths.left_ticket_done, route_key)

                try:
                    parsed_rows, _ = parse_left_ticket_payload(payload)
                except Exception as exc:
                    self._log_error("parse_left_ticket", {"route_key": route_key}, str(exc))
                    continue
                route_cache[route_key] = {row.train_no: row for row in parsed_rows}
                route_rows.append(
                    {
                        "query_date": self.config.query_date,
                        "from_station_code": from_code,
                        "to_station_code": to_code,
                        "result_count": str(len(parsed_rows)),
                        "fetched_at": self._now_iso(),
                    }
                )

            price_source = route_cache[route_key].get(summary.train_no)
            if price_source is not None:
                price_sources[summary.train_no] = price_source
        return price_sources, route_rows

    def _build_unique_route_keys(
        self,
        summaries: list[TrainSummary],
        station_name_index: dict[str, str],
    ) -> list[str]:
        keys: list[str] = []
        seen: set[str] = set()
        for summary in summaries:
            from_code = station_name_index.get(summary.start_station_name, "")
            to_code = station_name_index.get(summary.end_station_name, "")
            if not from_code or not to_code:
                continue
            route_key = f"{from_code}_{to_code}"
            if route_key in seen:
                continue
            seen.add(route_key)
            keys.append(route_key)
        return keys

    def _wrap_raw_record(
        self,
        *,
        endpoint: str,
        request_params: dict[str, str],
        response_body: dict,
    ) -> dict:
        return {
            "query_date": self.config.query_date,
            "fetched_at": self._now_iso(),
            "endpoint": endpoint,
            "request_params": request_params,
            "response_body": response_body,
        }

    def _log_error(self, endpoint: str, request_params: dict[str, str], message: str) -> None:
        append_jsonl(
            self.config.paths.error_log,
            {
                "query_date": self.config.query_date,
                "fetched_at": self._now_iso(),
                "endpoint": endpoint,
                "request_params": request_params,
                "message": message,
            },
        )

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _emit_progress(self, stage: str, current: int, total: int, detail: str = "") -> None:
        if not self.config.show_progress or total <= 0:
            return
        print(format_progress_message(stage, current, total, detail), file=sys.stderr, flush=True)
