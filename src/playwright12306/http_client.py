"""Shared HTTP client helpers for 12306 requests."""

from __future__ import annotations

from typing import Any

import requests


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)


def build_default_headers(referer: str) -> dict[str, str]:
    """Build a baseline header set for 12306 endpoints.

    Args:
        referer: The page that logically initiated the request.

    Returns:
        A header mapping suitable for JSON-like 12306 endpoints.
    """

    return {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": referer,
        "User-Agent": DEFAULT_USER_AGENT,
        "X-Requested-With": "XMLHttpRequest",
    }


def create_session() -> requests.Session:
    """Create a reusable session with a stable user agent."""

    session = requests.Session()
    session.headers.update({"User-Agent": DEFAULT_USER_AGENT})
    return session


def request_json(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    referer: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Perform a GET request and decode JSON safely."""

    response = session.get(
        url,
        params=params,
        headers=build_default_headers(referer),
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    text = response.text.lstrip("\ufeff\r\n\t ")
    if text.startswith("<!DOCTYPE") or text.startswith("<html"):
        snippet = text[:120].replace("\n", " ")
        raise ValueError(f"expected JSON but received HTML: {snippet}")
    try:
        return response.json()
    except ValueError as exc:
        snippet = text[:120].replace("\n", " ")
        raise ValueError(f"invalid JSON response: {snippet}") from exc
