"""The workflow: fetch last N daily points -> append to SQLite."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from bot_fx_workflow import db
from bot_fx_workflow.client import RatePoint, SupportsGet, fetch_daily_ref_rate
from bot_fx_workflow.config import Settings

BKK = timezone(timedelta(hours=7))
MAX_WINDOW_DAYS = 31  # BOT API limit per request


def today_bkk() -> date:
    return datetime.now(BKK).date()


def run(settings: Settings, *, today: date | None = None, session: SupportsGet | None = None) -> tuple[list[RatePoint], db.SaveResult]:
    end = today or today_bkk()
    earliest = end - timedelta(days=settings.lookback_days)

    # BOT rejects ranges over 31 days ("Exceed limit period"), so walk backwards
    # in windows of 31 days (inclusive) until we have enough points.
    by_period: dict[str, RatePoint] = {}
    win_end = end
    while win_end >= earliest and len(by_period) < settings.data_points:
        win_start = max(win_end - timedelta(days=MAX_WINDOW_DAYS - 1), earliest)
        for p in fetch_daily_ref_rate(settings.token, win_start, win_end, session=session):
            by_period[p.period] = p
        win_end = win_start - timedelta(days=1)
    points = sorted(by_period.values(), key=lambda p: p.period)[-settings.data_points :]

    conn = db.connect(settings.db_path)
    try:
        result = db.save_points(conn, points, datetime.now(timezone.utc).isoformat(timespec="seconds"))
    finally:
        conn.close()
    return points, result
