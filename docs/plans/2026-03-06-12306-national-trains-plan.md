# 12306 National Trains Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建一个纯 HTTP 的 12306 当日全国车次抓取程序，输出原始响应、时刻表和结构化价格，并支持断点续跑。

**Architecture:** 先通过 `queryTrainInfo/getTrainName` 获取当天全国车次种子，再逐车调用 `queryTrainInfo/query` 获取时刻表，用 `leftTicket/init + leftTicket/queryG` 抓取价格来源数据，并复用票价页前端逻辑解析 `infoAll_list`。余票与可售状态只做可选增强，不作为 MVP 硬要求。程序按模块拆分，先做可验证 MVP，再做增强。

**Tech Stack:** Python 3, requests, pandas, pytest

---

### Task 1: Create project skeleton

**Files:**
- Create: `src/playwright12306/__init__.py`
- Create: `src/playwright12306/config.py`
- Create: `scripts/fetch_national_trains.py`
- Create: `tests/test_smoke.py`

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_project_skeleton_exists() -> None:
    assert Path("src/playwright12306/__init__.py").exists()
    assert Path("src/playwright12306/config.py").exists()
    assert Path("scripts/fetch_national_trains.py").exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_smoke.py -q`
Expected: FAIL because files do not exist.

**Step 3: Write minimal implementation**

```python
"""playwright12306 package."""
```

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root: Path
```

```python
def main() -> int:
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_smoke.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/playwright12306/__init__.py src/playwright12306/config.py scripts/fetch_national_trains.py tests/test_smoke.py
git commit -m "feat: scaffold 12306 fetcher project"
```

### Task 2: Parse station codes

**Files:**
- Create: `src/playwright12306/stations.py`
- Create: `tests/test_stations.py`
- Test: `tests/test_stations.py`

**Step 1: Write the failing test**

```python
from playwright12306.stations import parse_station_names


def test_parse_station_names_extracts_station_code() -> None:
    raw = "var station_names ='@bji|北京|BJP|beijing|bj|2|0357|北京|||';"
    records = parse_station_names(raw)
    assert records["BJP"].name == "北京"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_stations.py -q`
Expected: FAIL with import error or missing function.

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class StationRecord:
    name: str
    telecode: str


def parse_station_names(raw: str) -> dict[str, StationRecord]:
    ...
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_stations.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/playwright12306/stations.py tests/test_stations.py
git commit -m "feat: parse 12306 station codes"
```

### Task 3: Build shared HTTP client

**Files:**
- Create: `src/playwright12306/http_client.py`
- Create: `tests/test_http_client.py`
- Modify: `src/playwright12306/config.py`

**Step 1: Write the failing test**

```python
from playwright12306.http_client import build_default_headers


def test_build_default_headers_contains_referer() -> None:
    headers = build_default_headers("https://kyfw.12306.cn/otn/leftTicket/init?linktypeid=dc")
    assert "Referer" in headers
    assert headers["User-Agent"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_http_client.py -q`
Expected: FAIL because helper does not exist.

**Step 3: Write minimal implementation**

```python
def build_default_headers(referer: str) -> dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0",
        "Referer": referer,
        "X-Requested-With": "XMLHttpRequest",
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_http_client.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/playwright12306/http_client.py src/playwright12306/config.py tests/test_http_client.py
git commit -m "feat: add shared 12306 http client"
```

### Task 4: Parse train seed response

**Files:**
- Create: `src/playwright12306/train_seed.py`
- Create: `tests/test_train_seed.py`

**Step 1: Write the failing test**

```python
from playwright12306.train_seed import parse_train_seed


def test_parse_train_seed_extracts_train_no() -> None:
    payload = {
        "status": True,
        "data": [{"station_train_code": "G1(北京南-上海虹桥)", "train_no": "24000000G10L"}],
    }
    rows = parse_train_seed(payload, query_date="2026-03-20")
    assert rows[0].train_no == "24000000G10L"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_train_seed.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class TrainSeed:
    query_date: str
    station_train_code: str
    train_no: str


def parse_train_seed(payload: dict, query_date: str) -> list[TrainSeed]:
    ...
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_train_seed.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/playwright12306/train_seed.py tests/test_train_seed.py
git commit -m "feat: parse daily train seed list"
```

### Task 5: Parse train schedule response

**Files:**
- Create: `src/playwright12306/train_info.py`
- Create: `tests/test_train_info.py`

**Step 1: Write the failing test**

```python
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
    assert len(result.stops) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_train_info.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
def parse_train_info(payload: dict, query_date: str, train_no: str):
    ...
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_train_info.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/playwright12306/train_info.py tests/test_train_info.py
git commit -m "feat: parse train schedule details"
```

### Task 6: Parse left ticket price-source rows

**Files:**
- Create: `src/playwright12306/left_ticket.py`
- Create: `tests/test_left_ticket.py`

**Step 1: Write the failing test**

```python
from playwright12306.left_ticket import parse_left_ticket_row


def test_parse_left_ticket_row_extracts_basic_fields() -> None:
    row = "|预订|24000000G520|G5|BJP|SHH|BJP|SHH|21:21|09:27|12:06|Y||||||||||||有|||||有||有||||J0O0I0|JOI|0|0||J054200021O036100021I068600021|0|||||1|0#1#0#0#z#0#JI#z|||CHN,CHN|||N#N#|||202603061000|Y|"
    parsed = parse_left_ticket_row(row)
    assert parsed.train_no == "24000000G520"
    assert parsed.station_train_code == "G5"
    assert parsed.from_station_code == "BJP"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_left_ticket.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
def parse_left_ticket_row(row: str):
    parts = row.split("|")
    ...
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_left_ticket.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/playwright12306/left_ticket.py tests/test_left_ticket.py
git commit -m "feat: parse left ticket price-source rows"
```

### Task 7: Parse structured seat prices

**Files:**
- Create: `src/playwright12306/price_parser.py`
- Create: `tests/test_price_parser.py`

**Step 1: Write the failing test**

```python
from playwright12306.price_parser import parse_info_all_list


def test_parse_info_all_list_extracts_second_class_price() -> None:
    prices = parse_info_all_list("O066903000#M107000000")
    assert prices["O"] == "66.9"
    assert prices["M"] == "107.0"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_price_parser.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
def parse_info_all_list(raw: str) -> dict[str, str]:
    ...
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_price_parser.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/playwright12306/price_parser.py tests/test_price_parser.py
git commit -m "feat: parse seat prices from infoAll_list"
```

### Task 8: Add state persistence and writers

**Files:**
- Create: `src/playwright12306/models.py`
- Create: `src/playwright12306/storage.py`
- Create: `tests/test_storage.py`

**Step 1: Write the failing test**

```python
from pathlib import Path
from playwright12306.storage import append_jsonl


def test_append_jsonl_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "rows.jsonl"
    append_jsonl(target, {"a": 1})
    assert target.exists()
    assert target.read_text(encoding="utf-8").strip()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
import json


def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/playwright12306/models.py src/playwright12306/storage.py tests/test_storage.py
git commit -m "feat: add storage helpers and state persistence"
```

### Task 9: Build pipeline orchestration

**Files:**
- Create: `src/playwright12306/pipeline.py`
- Create: `tests/test_pipeline_resume.py`
- Modify: `scripts/fetch_national_trains.py`

**Step 1: Write the failing test**

```python
from playwright12306.pipeline import should_skip_done_item


def test_should_skip_done_item() -> None:
    done = {"24000000G10L"}
    assert should_skip_done_item("24000000G10L", done) is True
    assert should_skip_done_item("24000000G520", done) is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline_resume.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
def should_skip_done_item(key: str, done: set[str]) -> bool:
    return key in done
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_pipeline_resume.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/playwright12306/pipeline.py scripts/fetch_national_trains.py tests/test_pipeline_resume.py
git commit -m "feat: add resumable fetch pipeline"
```

### Task 10: Add CLI arguments and end-to-end dry run

**Files:**
- Modify: `scripts/fetch_national_trains.py`
- Create: `tests/test_cli.py`

**Step 1: Write the failing test**

```python
from scripts.fetch_national_trains import build_parser


def test_build_parser_accepts_query_date() -> None:
    parser = build_parser()
    args = parser.parse_args(["--query-date", "2026-03-20"])
    assert args.query_date == "2026-03-20"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query-date", required=True)
    return parser
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/fetch_national_trains.py tests/test_cli.py
git commit -m "feat: add cli entrypoint for national train fetcher"
```

### Task 11: Verify the whole test suite

**Files:**
- Test: `tests/test_smoke.py`
- Test: `tests/test_stations.py`
- Test: `tests/test_http_client.py`
- Test: `tests/test_train_seed.py`
- Test: `tests/test_train_info.py`
- Test: `tests/test_left_ticket.py`
- Test: `tests/test_price_parser.py`
- Test: `tests/test_storage.py`
- Test: `tests/test_pipeline_resume.py`
- Test: `tests/test_cli.py`

**Step 1: Run the focused test suite**

Run: `pytest tests -q`
Expected: PASS with 0 failures.

**Step 2: Run a dry-run command**

Run: `python scripts/fetch_national_trains.py --query-date 2026-03-20 --dry-run`
Expected: command exits 0 and prints planned actions without hitting the network.

**Step 3: Commit**

```bash
git add tests
git commit -m "test: verify 12306 fetcher mvp"
```

### Task 12: Manual production verification

**Files:**
- Output: `artifacts/raw/`
- Output: `artifacts/normalized/`

**Step 1: Run the real fetch**

Run: `python scripts/fetch_national_trains.py --query-date 2026-03-20`
Expected: creates raw and normalized outputs under `artifacts/`.

**Step 2: Validate output files**

Run: `python - <<'PY'\nfrom pathlib import Path\nprint((Path('artifacts/normalized/trains.csv')).exists())\nprint((Path('artifacts/normalized/stops.csv')).exists())\nPY`
Expected: both lines print `True`.

**Step 3: Spot-check row counts and required price column**

Run: `python - <<'PY'\nimport pandas as pd\ntrains = pd.read_csv('artifacts/normalized/trains.csv')\nstops = pd.read_csv('artifacts/normalized/stops.csv')\nprint(trains.shape)\nprint(stops.shape)\nprint('seat_price_json' in trains.columns)\nPY`
Expected: non-zero row counts and the last line prints `True`.
