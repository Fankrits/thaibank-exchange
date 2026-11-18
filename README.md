# bot-fx-workflow

Fetches the last **20 daily data points** of the Bank of Thailand's
*Weighted-average Interbank Exchange Rate – THB / USD*, appends them to a local SQLite
database, and shows them in a dashboard.

- Data source: [BOT API Portal – Exchange Rates](https://portal.api.bot.or.th/portal/catalogue-products/exchange-rates-1)
- Endpoint: `https://gateway.api.bot.or.th/Stat-ReferenceRate/v2/DAILY_REF_RATE/`
- Output: `.venv/bot_api_daily_<Applicant_Name>.db` (table `daily_ref_rate`)

## 1. Prerequisites

| Tool | Check | Install |
|---|---|---|
| git | `git --version` | https://git-scm.com |
| uv | `uv --version` | https://docs.astral.sh/uv/getting-started/installation/ |

uv installs Python 3.12 for you, so no separate Python setup is needed.

You also need a **BOT API token**: sign in at <https://portal.api.bot.or.th>, create an
application, subscribe it to the **Exchange Rates** product, and copy its API key.

## 2. Clone and install

```bash
git clone <repo-url> bot-fx-workflow
cd bot-fx-workflow
uv sync
```

## 3. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
BOT_API_TOKEN=your_api_key_here
APPLICANT_NAME=Your_Name        # English name, used in the DB filename
```

`.env` is git-ignored — never commit your token.

## 4. Run

```bash
uv run bot-fx --dashboard
```

This fetches the data, saves it to SQLite, and opens the dashboard in your browser with the
data already loaded. Press `Ctrl+C` in the terminal to stop the local server.

Other ways to run it:

| Command | What it does |
|---|---|
| `uv run bot-fx` | Fetch and save only (prints the 5 latest rates) |
| `uv run bot-fx --dashboard` | Fetch, save, then open the dashboard |
| `uv run bot-fx-dashboard` | Open the dashboard on the data you already have |
| `uv run bot-fx --days 20 --lookback-days 45` | Options (these are the defaults) |
| `uv run pytest` | Run the tests (no token or internet needed) |

Running it again is safe: new days are added, existing days are not duplicated, and a day is
only updated if BOT revised its rate.

## 5. Where is my data?

The database is at `.venv/bot_api_daily_<Applicant_Name>.db`. `.venv` is a hidden folder.

```bash
sqlite3 -header -column .venv/bot_api_daily_Your_Name.db \
  "SELECT period, rate FROM daily_ref_rate ORDER BY period DESC;"
```

> Deleting `.venv` also deletes the database. Back the file up first if you need to recreate the environment.

## Troubleshooting

| Message | Fix |
|---|---|
| `BOT_API_TOKEN is not set` | Fill in `.env` (step 3) |
| `HTTP 401 … rejected the API key` | Wrong token, or the app isn't subscribed to **Exchange Rates** |
| `HTTP 429` | Rate limit is 200 calls/hour; wait and re-run |
| `warning: only N of 20 data points` | Long holiday period — add `--lookback-days 60` |
| `error: … not found. Run uv run bot-fx first.` | Fetch once before `bot-fx-dashboard` |

## More

- Full user guide (Thai, HTML): [docs/user-guide.html](docs/user-guide.html)
- Dashboard file: [docs/dashboard.html](docs/dashboard.html)
- For AI coding agents: [AGENTS.md](AGENTS.md)
