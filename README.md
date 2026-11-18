# bot-fx-workflow

Python workflow (uv) ที่ดึงข้อมูล **Weighted-average Interbank Exchange Rate – THB / USD** รายวันย้อนหลัง 20 วัน
จาก Bank of Thailand API แล้ว append ลง SQLite (`.venv/bot_api_daily_<ชื่อผู้สมัคร>.db`)

```bash
uv sync
cp .env.example .env      # ใส่ BOT_API_TOKEN
uv run bot-fx
uv run pytest
```

คู่มือฉบับเต็ม: [docs/user-guide.html](docs/user-guide.html) · สำหรับ AI agent: [AGENTS.md](AGENTS.md)
