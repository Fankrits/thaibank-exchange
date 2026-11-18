"""HTTP client for the BOT DAILY_REF_RATE endpoint."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

import requests

from bot_fx_workflow.config import ENDPOINT


class SupportsGet(Protocol):
    def get(self, url: str, *, params: Any = ..., headers: Any = ..., timeout: Any = ...) -> Any: ...


class BotApiError(RuntimeError):
    """Raised when the BOT API cannot give us usable data."""


@dataclass(frozen=True)
class RatePoint:
    period: str  # YYYY-MM-DD
    rate: float


def fetch_daily_ref_rate(
    token: str,
    start: date,
    end: date,
    *,
    session: SupportsGet | None = None,
    retries: int = 3,
    backoff: float = 1.5,
    timeout: float = 30.0,
) -> list[RatePoint]:
    """Return rate points for [start, end], sorted ascending by period.

    Auth is an ``Authorization`` header carrying the raw API key (no Bearer).
    Retries on network errors, HTTP 429 and 5xx; fails fast on 401/403/other 4xx.
    """
    http = session or requests.Session()
    params = {"start_period": start.isoformat(), "end_period": end.isoformat()}
    headers = {"Authorization": token, "Accept": "application/json"}

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            resp = http.get(ENDPOINT, params=params, headers=headers, timeout=timeout)
        except requests.RequestException as exc:
            last_err = exc
        else:
            if resp.status_code in (401, 403):
                raise BotApiError(
                    f"HTTP {resp.status_code}: BOT rejected the API key "
                    f"({_body_hint(resp)}). Check BOT_API_TOKEN and that your app "
                    "is subscribed to the 'Exchange Rates' product."
                )
            if resp.status_code == 429 or resp.status_code >= 500:
                last_err = BotApiError(f"HTTP {resp.status_code}: {_body_hint(resp)}")
            elif resp.status_code != 200:
                raise BotApiError(f"HTTP {resp.status_code}: {_body_hint(resp)}")
            else:
                return parse_response(resp)
        if attempt < retries - 1:
            time.sleep(backoff**attempt)
    raise BotApiError(f"BOT API unavailable after {retries} attempts: {last_err}")


def parse_response(resp: requests.Response) -> list[RatePoint]:
    try:
        payload = resp.json()
        detail = payload["result"]["data"]["data_detail"]
    except (ValueError, KeyError, TypeError) as exc:
        raise BotApiError(f"Unexpected response shape: {exc!r}; body={resp.text[:200]!r}") from exc

    if isinstance(detail, dict):  # tolerate a single-object payload
        detail = [detail]

    points: list[RatePoint] = []
    for row in detail or []:
        period, raw = row.get("period"), row.get("rate")
        try:
            points.append(RatePoint(period=str(period), rate=float(raw or "")))
        except (TypeError, ValueError):
            continue  # skip days with an empty / non-numeric rate
    points.sort(key=lambda p: p.period)
    return points


def _body_hint(resp: requests.Response) -> str:
    return resp.text.strip().replace("\n", " ")[:160]
