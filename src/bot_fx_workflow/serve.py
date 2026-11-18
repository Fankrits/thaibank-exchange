"""Tiny local web server: opens docs/dashboard.html with the DB already loaded.

Only two things are ever served — the dashboard page and the one DB file — so
secrets such as ``.env`` are never exposed. Binds to 127.0.0.1 only.
"""

from __future__ import annotations

import argparse
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from dotenv import load_dotenv

from bot_fx_workflow import config

DASHBOARD = config.PROJECT_ROOT / "docs" / "dashboard.html"


def make_server(db_path: Path, dashboard: Path = DASHBOARD, port: int = 8765) -> ThreadingHTTPServer:
    db_name = db_path.name

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, ctype: str, extra: dict[str, str] | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 (http.server API)
            url = urlparse(self.path)
            if url.path in ("/", "/index.html", "/dashboard.html"):
                if parse_qs(url.query).get("db") != [db_name]:
                    self._send(302, b"", "text/plain", {"Location": f"/?db={quote(db_name)}"})
                else:
                    self._send(200, dashboard.read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/" + quote(db_name) and db_path.exists():
                self._send(200, db_path.read_bytes(), "application/octet-stream")
            elif url.path == "/favicon.ico":
                self._send(204, b"", "image/x-icon")
            else:
                self._send(404, b"not found", "text/plain")

        def log_message(self, *args: object) -> None:  # keep the terminal quiet
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv: list[str] | None = None) -> int:
    load_dotenv(config.PROJECT_ROOT / ".env")
    p = argparse.ArgumentParser(prog="bot-fx-dashboard", description="Open the dashboard with the DB auto-loaded.")
    p.add_argument("--applicant", help="applicant name (selects the DB file; env: APPLICANT_NAME)")
    p.add_argument("--db-path", type=Path, help="DB file (default .venv/bot_api_daily_<applicant>.db)")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-open", action="store_true", help="do not launch a browser")
    args = p.parse_args(argv)

    import os

    name = args.applicant or os.environ.get("APPLICANT_NAME") or config.DEFAULT_APPLICANT
    db_path = (args.db_path or config.default_db_path(name)).expanduser()
    if not db_path.exists():
        print(f"error: {db_path} not found. Run `uv run bot-fx` first.")
        return 1
    return serve(db_path, args.port, open_browser=not args.no_open)


def serve(db_path: Path, port: int = 8765, *, open_browser: bool = True) -> int:
    server = make_server(db_path, port=port)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"dashboard: {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.4, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()
    return 0
