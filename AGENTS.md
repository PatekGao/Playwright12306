# Repository Guidelines

## Project Structure & Module Organization

This repository is currently a PyCharm/Python project (see `.idea/`). When adding code, keep it organized and easy to test:

- `src/`: Python package code (recommended: `src/playwright12306/`)
- `scripts/`: runnable entry points (e.g., `scripts/login.py`, `scripts/query_tickets.py`)
- `tests/`: automated tests and fixtures
- `assets/` or `fixtures/`: stable HTML/screenshot fixtures used by tests

## Build, Test, and Development Commands

The repo does not yet include a locked dependency setup; use the commands below as the baseline workflow:

- Create a venv: `python -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt` (or `pip install -e .[dev]` if packaging)
- Install Playwright browsers: `python -m playwright install`
- Run scripts: `python scripts/<name>.py --help`
- Run tests: `pytest -q`

## Coding Style & Naming Conventions

- Python: 4-space indentation, `snake_case` for modules/functions, `PascalCase` for classes.
- Prefer type hints for public functions and shared utilities.
- Centralize selectors/locators (e.g., `src/playwright12306/locators.py`) to reduce flaky tests.

## Testing Guidelines

- Prefer `pytest`; name files `test_*.py` and keep tests deterministic.
- Avoid real purchases or irreversible actions; use fixtures/stubs and dry-run modes.
- Write Playwright traces/screenshots to an `artifacts/` directory and keep it out of Git.

## Commit & Pull Request Guidelines

Git history is not present in this directory; use Conventional Commits by default (`feat:`, `fix:`, `docs:`, `chore:`).

- Keep commits focused and descriptive (imperative mood).
- PRs should include: a short summary, linked issue (if any), and a screenshot/video for UI/selector changes.

## Security & Configuration Tips

- Never commit credentials, cookies, or personal data; use environment variables or a local `.env` file.
- Redact logs/traces/screenshots before sharing if they may contain sensitive information.
