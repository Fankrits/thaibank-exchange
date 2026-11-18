# AGENTS.md

Python workflow: pull the last 20 daily **Weighted-average Interbank Exchange Rate (THB/USD)** points from the
Bank of Thailand API and append them to a SQLite file. Managed with **uv**.

## Commands
- `uv sync` — create `.venv` and install deps
- `uv run bot-fx` — run the workflow (needs `BOT_API_TOKEN`)
- `uv run pytest` — run tests (no network or token needed)

## Layout
- `src/bot_fx_workflow/config.py` — endpoint, defaults, settings, DB path
- `client.py` — HTTP call + response parsing (`Authorization` header, retries)
- `db.py` — SQLite schema + upsert (`daily_ref_rate`, PK = `period`)
- `workflow.py` — fetch window -> keep latest N -> save
- `cli.py` — argparse entry point (`bot-fx`)
- `docs/user-guide.html` — end-user manual (Thai)
- `docs/dashboard.html` — single-file viewer for the DB (sql.js + Chart.js, shadcn zinc tokens/classes on Tailwind v4 CDN); reads table `daily_ref_rate`, so update it if the schema changes

## Facts that must stay true
- Endpoint: `https://gateway.api.bot.or.th/Stat-ReferenceRate/v2/DAILY_REF_RATE/`, params `start_period`, `end_period` (`YYYY-MM-DD`).
- Auth: raw API key in the `Authorization` header (no `Bearer`). Read from `BOT_API_TOKEN` (env or `.env`). Never commit it.
- BOT publishes business days only and **rejects ranges over 31 days** (HTTP 400 "Exceed limit period"). The workflow walks backwards in <=31-day windows (max 45 days back) until it has 20 points, and keeps the **latest 20**.
- DB file: `.venv/bot_api_daily_{Applicant_Name_Eng}.db` (name from `APPLICANT_NAME` / `--applicant`). Rows are appended; re-runs are idempotent (insert new `period`, update only if rate changed).
- Rate limit of the "Exchange Rates Plan": 200 calls / hour. One run = 1 call.

## Conventions
- Keep dependencies minimal (`requests`, `python-dotenv`). Add tests in `tests/` using the fake session, not live calls.
- Changing the DB schema or filename pattern: update `docs/user-guide.html` too.
