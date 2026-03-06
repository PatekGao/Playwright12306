from pathlib import Path


def test_project_skeleton_exists() -> None:
    assert Path("src/playwright12306/__init__.py").exists()
    assert Path("src/playwright12306/config.py").exists()
    assert Path("scripts/fetch_national_trains.py").exists()
