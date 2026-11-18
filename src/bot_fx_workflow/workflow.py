"""The workflow: fetch last N daily points -> append to SQLite."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from bot_fx_workflow import db
from bot_fx_workflow.client import RatePoint, SupportsGet, fetch_daily_ref_rate
from bot_fx_workflow.config import Settings

BKK = timezone(timedelta(hours=7))


def today_bkk() -> date:
    return datetime.now(BKK).date()


def run(settings: Settings, *, today: date | None = None, session: SupportsGet | None = None) -> tuple[list[RatePoint], db.SaveResult]:
    end = today or today_bkk()
    start = end - timedelta(days=settings.lookback_days)
    points = fetch_daily_ref_rate(settings.token, start, end, session=session)
    points = points[-settings.data_points :]  # the most recent N business days

    conn = db.connect(settings.db_path)
    try:
        result = db.save_points(conn, points, datetime.now(timezone.utc).isoformat(timespec="seconds"))
    finally:
        conn.close()
    return points, result
