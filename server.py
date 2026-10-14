#!/usr/bin/env python3
"""Local-only HTTP server for the Silo Swarm demo."""

from __future__ import annotations

import json
import signal
import threading
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from audit import AuditLogger

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DATA = ROOT / "data" / "demo-run.json"
LOGGER = AuditLogger(ROOT / "logs")
RUN = json.loads(DATA.read_text(encoding="utf-8"))
SESSION_ID = RUN["run_id"]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def log_message(self, _format: str, *_args) -> None:
        return

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _audit(self, action: str, target: str, outcome: str) -> None:
        LOGGER.append(
            actor="local-browser",
            action=action,
            target=target,
            outcome=outcome,
            details={"transport": "loopback-http", "method": "GET"},
            session_id=SESSION_ID,
            request_id=str(uuid.uuid4()),
        )

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/run":
            self._audit("demo.data.read", "sealed-run", "success")
            self._json(RUN)
            return
        if path == "/api/audit-status":
            try:
                status = LOGGER.verify()
                self._audit("audit.chain.verified", "logs/audit.jsonl", "success")
                self._json(status)
            except Exception as exc:
                self._audit("audit.chain.verified", "logs/audit.jsonl", "failure")
                self._json({"valid": False, "error": type(exc).__name__}, 500)
            return
        if path == "/":
            self.path = "/index.html"
        super().do_GET()


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    LOGGER.append(
        actor="demo-server",
        action="server.started",
        target="127.0.0.1:8765",
        outcome="success",
        details={"network_scope": "loopback-only"},
        session_id=SESSION_ID,
    )

    def shutdown(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    try:
        server.serve_forever()
    finally:
        LOGGER.append(
            actor="demo-server",
            action="server.stopped",
            target="127.0.0.1:8765",
            outcome="success",
            details={"reason": "signal-or-exit"},
            session_id=SESSION_ID,
        )
        server.server_close()


if __name__ == "__main__":
    main()
