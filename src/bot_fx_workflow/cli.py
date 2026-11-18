"""Command line entry point: ``uv run bot-fx``."""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from bot_fx_workflow import db, workflow
from bot_fx_workflow.client import BotApiError
from bot_fx_workflow.config import (
    DEFAULT_DATA_POINTS,
    DEFAULT_LOOKBACK_DAYS,
    PROJECT_ROOT,
    load_settings,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bot-fx",
        description="Fetch daily THB/USD weighted-average interbank rates from the BOT API into SQLite.",
    )
    p.add_argument("--applicant", help="English applicant name used in the DB filename (env: APPLICANT_NAME)")
    p.add_argument("--days", type=int, default=DEFAULT_DATA_POINTS, help="number of daily data points (default 20)")
    p.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS, help="max calendar days to look back (default 45, requested in <=31-day windows)")
    p.add_argument("--db-path", type=Path, help="override DB path (default .venv/bot_api_daily_<applicant>.db)")
    return p


def main(argv: list[str] | None = None) -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    args = build_parser().parse_args(argv)
    if args.days < 1:
        raise SystemExit("--days must be >= 1")
    settings = load_settings(
        applicant=args.applicant,
        db_path=args.db_path,
        data_points=args.days,
        lookback_days=args.lookback_days,
    )
    try:
        points, result = workflow.run(settings)
    except BotApiError as exc:
        print(f"error: {exc}")
        return 1

    if len(points) < settings.data_points:
        print(f"warning: only {len(points)} of {settings.data_points} data points returned; "
              "try a larger --lookback-days")
    print(f"fetched {len(points)} points ({points[0].period} .. {points[-1].period})" if points else "fetched 0 points")
    print(f"inserted={result.inserted} updated={result.updated} unchanged={result.unchanged}")
    print(f"db: {settings.db_path}")
    conn = db.connect(settings.db_path)
    try:
        for period, rate in db.latest(conn, 5):
            print(f"  {period}  {rate:.4f}")
    finally:
        conn.close()
    return 0
