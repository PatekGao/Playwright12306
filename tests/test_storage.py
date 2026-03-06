from pathlib import Path

from playwright12306.storage import append_jsonl, write_csv


def test_append_jsonl_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "rows.jsonl"
    append_jsonl(target, {"a": 1})
    assert target.exists()
    assert target.read_text(encoding="utf-8").strip()


def test_write_csv_uses_utf8_bom_for_excel_compatibility(tmp_path: Path) -> None:
    target = tmp_path / "rows.csv"
    write_csv(target, [{"city": "北京"}])
    assert target.exists()
    assert target.read_bytes().startswith(b"\xef\xbb\xbf")
