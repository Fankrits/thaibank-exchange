import sqlite3
from datetime import date

import pytest

from bot_fx_workflow import db, workflow
from bot_fx_workflow.client import BotApiError, fetch_daily_ref_rate
from bot_fx_workflow.config import Settings, default_db_path, safe_name


class FakeResp:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code, self._payload, self.text = status, payload, text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeSession:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, *, params=None, headers=None, timeout=None):
        self.calls.append((url, params, headers))
        return self.responses.pop(0)


def payload(rows):
    return {"result": {"data": {"data_header": {}, "data_detail": rows}}}


def business_days(n):
    # n consecutive fake days, returned newest-first like the real API
    return [{"period": f"2026-10-{d:02d}", "rate": f"32.{d:02d}00000"} for d in range(n, 0, -1)]


def settings(tmp_path, points=20):
    return Settings("tok", "Test_User", tmp_path / "x" / "t.db", points, 45)


def test_name_and_path(tmp_path):
    assert safe_name(" Kritsada  Nhanjeing ") == "Kritsada_Nhanjeing"
    assert default_db_path("A B", tmp_path) == tmp_path / ".venv" / "bot_api_daily_A_B.db"


def test_sends_raw_authorization_header_and_dates():
    s = FakeSession(FakeResp(payload=payload([])))
    fetch_daily_ref_rate("secret", date(2026, 10, 1), date(2026, 11, 17), session=s)
    url, params, headers = s.calls[0]
    assert url.endswith("/Stat-ReferenceRate/v2/DAILY_REF_RATE/")
    assert params == {"start_period": "2026-10-01", "end_period": "2026-11-17"}
    assert headers["Authorization"] == "secret"


def test_keeps_latest_20_and_is_idempotent(tmp_path):
    st = settings(tmp_path)
    s = FakeSession(FakeResp(payload=payload(business_days(25))), FakeResp(payload=payload(business_days(25))))
    points, r1 = workflow.run(st, today=date(2026, 11, 1), session=s)
    assert len(points) == 20 and points[0].period == "2026-10-06" and points[-1].period == "2026-10-25"
    assert (r1.inserted, r1.updated) == (20, 0)

    _, r2 = workflow.run(st, today=date(2026, 11, 1), session=s)
    assert (r2.inserted, r2.updated, r2.unchanged) == (0, 0, 20)
    assert sqlite3.connect(st.db_path).execute("select count(*) from daily_ref_rate").fetchone()[0] == 20


def test_append_new_day_and_revision(tmp_path):
    st = settings(tmp_path)
    conn = db.connect(st.db_path)
    from bot_fx_workflow.client import RatePoint

    db.save_points(conn, [RatePoint("2026-10-01", 32.0)], "t0")
    r = db.save_points(conn, [RatePoint("2026-10-01", 32.5), RatePoint("2026-10-02", 32.1)], "t1")
    assert (r.inserted, r.updated, r.unchanged) == (1, 1, 0)
    assert db.latest(conn, 5) == [("2026-10-02", 32.1), ("2026-10-01", 32.5)]


def test_skips_bad_rows(tmp_path):
    s = FakeSession(FakeResp(payload=payload([{"period": "2026-10-01", "rate": ""}, {"period": "2026-10-02", "rate": "32.1"}])))
    pts = fetch_daily_ref_rate("t", date(2026, 10, 1), date(2026, 10, 2), session=s)
    assert [p.period for p in pts] == ["2026-10-02"]


def test_auth_error_fails_fast():
    s = FakeSession(FakeResp(401, text='{"error": "Authorization field missing"}'))
    with pytest.raises(BotApiError, match="rejected the API key"):
        fetch_daily_ref_rate("", date(2026, 10, 1), date(2026, 10, 2), session=s)
    assert len(s.calls) == 1


def test_retries_5xx_then_succeeds(monkeypatch):
    monkeypatch.setattr("bot_fx_workflow.client.time.sleep", lambda _: None)
    s = FakeSession(FakeResp(503, text="x"), FakeResp(payload=payload(business_days(2))))
    assert len(fetch_daily_ref_rate("t", date(2026, 10, 1), date(2026, 10, 2), session=s)) == 2
    assert len(s.calls) == 2


def test_windows_never_exceed_31_days_and_stop_early(tmp_path):
    # window 1 has only 12 points -> a 2nd window is requested; 3rd is not needed
    s = FakeSession(
        FakeResp(payload=payload(business_days(12))),
        FakeResp(payload=payload([{"period": f"2026-09-{d:02d}", "rate": "31.5"} for d in range(20, 10, -1)])),
    )
    points, r = workflow.run(settings(tmp_path), today=date(2026, 11, 18), session=s)
    assert len(s.calls) == 2 and len(points) == 20 and r.inserted == 20
    for _, params, _ in s.calls:
        a, b = date.fromisoformat(params["start_period"]), date.fromisoformat(params["end_period"])
        assert (b - a).days + 1 <= 31
    assert date.fromisoformat(s.calls[1][1]["end_period"]) < date.fromisoformat(s.calls[0][1]["start_period"])


def test_dashboard_server_serves_only_page_and_db(tmp_path):
    import threading
    import urllib.error
    import urllib.request

    from bot_fx_workflow.serve import make_server

    db_file = tmp_path / "bot_api_daily_T.db"
    db_file.write_bytes(b"SQLite format 3\x00fake")
    page = tmp_path / "dash.html"
    page.write_text("<html>dash</html>")
    (tmp_path / ".env").write_text("BOT_API_TOKEN=secret")
    srv = make_server(db_file, page, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    try:
        assert urllib.request.urlopen(f"{base}/?db=bot_api_daily_T.db").read() == b"<html>dash</html>"
        assert urllib.request.urlopen(f"{base}/bot_api_daily_T.db").read().startswith(b"SQLite format 3")
        for bad in ("/.env", "/pyproject.toml", "/../.env"):
            with pytest.raises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(base + bad)
            assert e.value.code == 404
    finally:
        srv.shutdown()
