from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bootstrap import create_app_context
from app.web import get_auth_status, get_dashboard_payload, get_notification_payload, get_settings_payload


class RequestHandler(BaseHTTPRequestHandler):
    context = create_app_context()

    def do_GET(self) -> None:  # noqa: N802
        routes = {
            "/health": {"status": "ok"},
            "/dashboard": get_dashboard_payload(self.context),
            "/notifications": get_notification_payload(self.context),
            "/settings": get_settings_payload(self.context),
            "/auth": get_auth_status(self.context),
        }
        payload = routes.get(self.path)
        if payload is None:
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 8000), RequestHandler)
    print("web skeleton listening on http://127.0.0.1:8000")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

