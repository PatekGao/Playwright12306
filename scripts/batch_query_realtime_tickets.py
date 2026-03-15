from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from importlib import import_module
import json
from pathlib import Path
import re
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pandas as pd


DEFAULT_SHEET_NAME = "queries"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "realtime-batch"
TRUE_VALUES = {"1", "true", "y", "yes", "on"}
FALSE_VALUES = {"0", "false", "n", "no", "off"}
TEMPLATE_COLUMNS = [
    "enabled",
    "date",
    "date_from",
    "date_to",
    "query_scope",
    "from_station_name",
    "to_station_name",
    "train_code",
    "train_class_name",
    "note",
]
TEMPLATE_ROWS = [
    {
        "enabled": "Y",
        "date": "2026-03-18",
        "date_from": "",
        "date_to": "",
        "query_scope": "city",
        "from_station_name": "上海",
        "to_station_name": "北京",
        "train_code": "",
        "train_class_name": "",
        "note": "单日城市对",
    },
    {
        "enabled": "Y",
        "date": "",
        "date_from": "2026-03-18",
        "date_to": "2026-03-20",
        "query_scope": "city",
        "from_station_name": "杭州",
        "to_station_name": "上海",
        "train_code": "",
        "train_class_name": "高速",
        "note": "日期范围城市对",
    },
    {
        "enabled": "N",
        "date": "2026-03-18",
        "date_from": "",
        "date_to": "",
        "query_scope": "station",
        "from_station_name": "杭州东",
        "to_station_name": "上海虹桥",
        "train_code": "G2",
        "train_class_name": "",
        "note": "禁用示例行",
    },
]


@dataclass(frozen=True)
class BatchRunResult:
    total_rows: int
    executed_rows: int
    succeeded_rows: int
    failed_rows: int
    skipped_rows: int
    summary_csv: Path
    summary_xlsx: Path
    details_dir: Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run realtime 12306 queries from an Excel workbook."
    )
    parser.add_argument(
        "--input-xlsx",
        required=True,
        help="Excel workbook path. The default sheet name is 'queries'.",
    )
    parser.add_argument(
        "--sheet-name",
        default=DEFAULT_SHEET_NAME,
        help="Worksheet name that stores batch query rows.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for summary files and per-row JSON results.",
    )
    return parser


def build_template_dataframe() -> pd.DataFrame:
    return pd.DataFrame(TEMPLATE_ROWS, columns=TEMPLATE_COLUMNS)


def write_example_workbook(target: Path, *, sheet_name: str = DEFAULT_SHEET_NAME) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    dataframe = build_template_dataframe()
    with pd.ExcelWriter(target) as writer:
        dataframe.to_excel(writer, index=False, sheet_name=sheet_name)
    return target


def normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def normalize_enabled_flag(value: Any) -> bool:
    text = normalize_cell(value).lower()
    if not text:
        return True
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    raise ValueError(f"invalid enabled value: {value}")


def slugify_filename_part(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "-", value.strip())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "query"


def load_batch_rows(input_xlsx: Path, *, sheet_name: str) -> list[dict[str, Any]]:
    try:
        dataframe = pd.read_excel(input_xlsx, sheet_name=sheet_name, dtype=object)
    except ImportError as exc:
        raise RuntimeError(
            "reading Excel requires openpyxl; install dependencies from requirements.txt first"
        ) from exc

    rows: list[dict[str, Any]] = []
    for row_index, record in enumerate(dataframe.to_dict(orient="records"), start=2):
        normalized: dict[str, Any] = {
            str(key): normalize_cell(value) for key, value in record.items()
        }
        normalized["__row_number__"] = row_index
        rows.append(normalized)
    return rows


def build_request_payload(row: dict[str, Any]) -> dict[str, str]:
    return {
        "date": row.get("date", ""),
        "date_from": row.get("date_from", ""),
        "date_to": row.get("date_to", ""),
        "query_scope": row.get("query_scope", "") or "city",
        "from_station_name": row.get("from_station_name", ""),
        "to_station_name": row.get("to_station_name", ""),
        "train_code": row.get("train_code", ""),
        "train_class_name": row.get("train_class_name", ""),
    }


def summarize_result(result: dict[str, Any]) -> dict[str, Any]:
    request = result["request"]
    summary = result["summary"]
    return {
        "query_mode": request["query_mode"],
        "query_scope": request["query_scope"],
        "date_from": request["date_from"],
        "date_to": request["date_to"],
        "from_station_name": request["from_station_name"],
        "to_station_name": request["to_station_name"],
        "train_code": request["train_code"],
        "train_class_name": request["train_class_name"],
        "matched_train_count": summary["matched_train_count"],
        "available_train_count": summary["available_train_count"],
        "failed_days": summary["failed_days"],
        "successful_days": summary["successful_days"],
        "cheapest_available_price": summary["cheapest_available_price"],
        "fastest_duration": summary["fastest_duration"],
        "partial_failure_count": len(result.get("partial_failures", [])),
    }


def write_summary_files(output_dir: Path, summary_rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    summary_csv = output_dir / "batch_summary.csv"
    summary_xlsx = output_dir / "batch_summary.xlsx"
    dataframe = pd.DataFrame(summary_rows)
    dataframe.to_csv(summary_csv, index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(summary_xlsx) as writer:
        dataframe.to_excel(writer, index=False, sheet_name="summary")
    return summary_csv, summary_xlsx


def run_batch_queries(
    input_xlsx: Path,
    *,
    sheet_name: str = DEFAULT_SHEET_NAME,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    service: Any = None,
) -> BatchRunResult:
    rows = load_batch_rows(input_xlsx, sheet_name=sheet_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    details_dir = output_dir / "details"
    details_dir.mkdir(parents=True, exist_ok=True)

    if service is None:
        realtime_module = import_module("playwright12306.realtime")
        query_service = realtime_module.RealtimeQueryService()
    else:
        query_service = service
    summary_rows: list[dict[str, Any]] = []
    executed_rows = 0
    succeeded_rows = 0
    failed_rows = 0
    skipped_rows = 0

    for row in rows:
        row_number = row["__row_number__"]
        note = row.get("note", "")
        try:
            enabled = normalize_enabled_flag(row.get("enabled", ""))
        except ValueError as exc:
            failed_rows += 1
            summary_rows.append(
                {
                    "row_number": row_number,
                    "status": "failed",
                    "note": note,
                    "error": str(exc),
                }
            )
            continue

        if not enabled:
            skipped_rows += 1
            summary_rows.append(
                {
                    "row_number": row_number,
                    "status": "skipped",
                    "note": note,
                    "error": "disabled",
                }
            )
            continue

        payload = build_request_payload(row)
        try:
            realtime_module = import_module("playwright12306.realtime")
            request = realtime_module.normalize_realtime_request(payload)
            result = query_service.run_query(request)
        except Exception as exc:
            executed_rows += 1
            failed_rows += 1
            summary_rows.append(
                {
                    "row_number": row_number,
                    "status": "failed",
                    "note": note,
                    **payload,
                    "error": str(exc),
                }
            )
            continue

        executed_rows += 1
        succeeded_rows += 1
        result_stem = (
            f"row-{row_number:03d}_"
            f"{slugify_filename_part(request.from_station_name)}_"
            f"{slugify_filename_part(request.to_station_name or request.train_code or request.query_mode)}"
        )
        result_path = details_dir / f"{result_stem}.json"
        result_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        summary_rows.append(
            {
                "row_number": row_number,
                "status": "completed",
                "note": note,
                **summarize_result(result),
                "error": "",
                "result_json": str(result_path.relative_to(output_dir)),
            }
        )

    summary_csv, summary_xlsx = write_summary_files(output_dir, summary_rows)
    return BatchRunResult(
        total_rows=len(rows),
        executed_rows=executed_rows,
        succeeded_rows=succeeded_rows,
        failed_rows=failed_rows,
        skipped_rows=skipped_rows,
        summary_csv=summary_csv,
        summary_xlsx=summary_xlsx,
        details_dir=details_dir,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_batch_queries(
        Path(args.input_xlsx).expanduser(),
        sheet_name=args.sheet_name,
        output_dir=Path(args.output_dir).expanduser(),
    )
    print(f"total_rows={result.total_rows}")
    print(f"executed_rows={result.executed_rows}")
    print(f"succeeded_rows={result.succeeded_rows}")
    print(f"failed_rows={result.failed_rows}")
    print(f"skipped_rows={result.skipped_rows}")
    print(result.summary_csv)
    print(result.summary_xlsx)
    print(result.details_dir)
    return 0 if result.failed_rows == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
