from __future__ import annotations

import csv
import sqlite3

from playwright12306.search_importer import import_artifacts
from tests.search_test_support import write_sample_artifacts_dir


def test_import_artifacts_creates_expected_tables_and_rows(tmp_path) -> None:
    artifacts_dir = write_sample_artifacts_dir(tmp_path / "artifacts" / "2026-03-18")
    db_path = tmp_path / "data" / "train_search.db"

    result = import_artifacts(artifacts_dir=artifacts_dir, db_path=db_path)

    assert result.query_date == "2026-03-18"
    assert result.train_count == 2
    assert result.stop_count == 5
    assert result.route_count == 2
    assert result.seat_price_count == 4
    assert db_path.exists()

    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("select count(*) from trains").fetchone()[0] == 2
        assert conn.execute("select count(*) from stops").fetchone()[0] == 5
        assert conn.execute("select count(*) from routes").fetchone()[0] == 2
        assert conn.execute("select count(*) from seat_prices").fetchone()[0] == 4
        assert conn.execute("select count(*) from import_batches").fetchone()[0] == 1
        seat_row = conn.execute(
            """
            select seat_name, price
            from seat_prices
            where query_date = '2026-03-18' and train_no = '24000000G20X' and seat_code = 'O'
            """
        ).fetchone()
    finally:
        conn.close()

    assert seat_row == ("二等座", 73.0)


def test_import_artifacts_deduplicates_rows_by_primary_key(tmp_path) -> None:
    artifacts_dir = write_sample_artifacts_dir(tmp_path / "artifacts" / "2026-03-18")
    db_path = tmp_path / "data" / "train_search.db"
    trains_path = artifacts_dir / "normalized" / "trains.csv"
    stops_path = artifacts_dir / "normalized" / "stops.csv"

    _append_duplicate_first_row(trains_path)
    _append_duplicate_first_row(stops_path)

    result = import_artifacts(artifacts_dir=artifacts_dir, db_path=db_path)

    assert result.train_count == 2
    assert result.stop_count == 5

    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("select count(*) from trains").fetchone()[0] == 2
        assert conn.execute("select count(*) from stops").fetchone()[0] == 5
    finally:
        conn.close()


def _append_duplicate_first_row(path) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows + [rows[0]])
