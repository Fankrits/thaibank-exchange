"""Configuration: constants and settings resolved from env / CLI."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

ENDPOINT = "https://gateway.api.bot.or.th/Stat-ReferenceRate/v2/DAILY_REF_RATE/"
API_NAME = "Weighted-average Interbank Exchange Rate - THB / USD"
CURRENCY_PAIR = "THB/USD"

DEFAULT_APPLICANT = "Kritsada_Nhanjeing"
DEFAULT_DATA_POINTS = 20
# BOT only publishes on business days, so 20 data points need a wider calendar
# window (weekends + Thai public holidays). 45 days comfortably covers 20 points.
DEFAULT_LOOKBACK_DAYS = 45

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    token: str
    applicant: str
    db_path: Path
    data_points: int
    lookback_days: int


def safe_name(name: str) -> str:
    """Make an applicant name safe for use in a filename."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", name.strip()).strip("_")
    if not cleaned:
        raise ValueError("applicant name must contain at least one latin letter or digit")
    return cleaned


def default_db_path(applicant: str, root: Path = PROJECT_ROOT) -> Path:
    """bot_api_daily_{applicant}.db inside the project's .venv directory."""
    return root / ".venv" / f"bot_api_daily_{safe_name(applicant)}.db"


def load_settings(
    *,
    applicant: str | None = None,
    db_path: Path | None = None,
    data_points: int = DEFAULT_DATA_POINTS,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> Settings:
    token = os.environ.get("BOT_API_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "BOT_API_TOKEN is not set. Put your BOT API key in .env "
            "(see .env.example) or export it in your shell."
        )
    name = applicant or os.environ.get("APPLICANT_NAME") or DEFAULT_APPLICANT
    path = db_path or (Path(os.environ["BOT_DB_PATH"]) if os.environ.get("BOT_DB_PATH") else None)
    return Settings(
        token=token,
        applicant=safe_name(name),
        db_path=(path or default_db_path(name)).expanduser(),
        data_points=data_points,
        lookback_days=max(lookback_days, data_points),
    )
