"""SQLite storage. Rows are appended; re-runs never create duplicates."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from bot_fx_workflow.client import RatePoint
from bot_fx_workflow.config import API_NAME, CURRENCY_PAIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_ref_rate (
    period        TEXT PRIMARY KEY,           -- YYYY-MM-DD (business day)
    rate          REAL NOT NULL,              -- THB per 1 USD
    currency_pair TEXT NOT NULL,
    source_api    TEXT NOT NULL,
    fetched_at    TEXT NOT NULL               -- UTC ISO timestamp of the run that wrote it
);
"""


@dataclass(frozen=True)
class SaveResult:
    inserted: int
    updated: int
    unchanged: int


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(SCHEMA)
    return conn


def save_points(conn: sqlite3.Connection, points: list[RatePoint], fetched_at: str) -> SaveResult:
    """Append new days; update a day only if BOT revised its rate."""
    inserted = updated = unchanged = 0
    with conn:
        for p in points:
            row = conn.execute(
                "SELECT rate FROM daily_ref_rate WHERE period = ?", (p.period,)
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO daily_ref_rate VALUES (?, ?, ?, ?, ?)",
                    (p.period, p.rate, CURRENCY_PAIR, API_NAME, fetched_at),
                )
                inserted += 1
            elif row[0] != p.rate:
                conn.execute(
                    "UPDATE daily_ref_rate SET rate = ?, fetched_at = ? WHERE period = ?",
                    (p.rate, fetched_at, p.period),
                )
                updated += 1
            else:
                unchanged += 1
    return SaveResult(inserted, updated, unchanged)


def latest(conn: sqlite3.Connection, n: int) -> list[tuple[str, float]]:
    return conn.execute(
        "SELECT period, rate FROM daily_ref_rate ORDER BY period DESC LIMIT ?", (n,)
    ).fetchall()
