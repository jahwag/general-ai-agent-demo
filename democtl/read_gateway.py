from __future__ import annotations

import argparse
import json
import os
import socketserver
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit

from .freshworks import FreshworksClient, FreshworksConfig


class DemoTicketApplication:
    """Read-only application exposing exactly one configured demo ticket."""

    def __init__(self, client: FreshworksClient, ticket_id: int) -> None:
        if ticket_id < 1:
            raise ValueError("DEMO_TICKET_ID must be a positive integer")
        self.client = client
        self.ticket_id = ticket_id

    def get(self, path: str) -> tuple[int, dict[str, object]]:
        requested_path = urlsplit(path).path
        if requested_path != f"/api/demo/tickets/{self.ticket_id}":
            return 404, {"error": "demo ticket not found"}
        return 200, self.client.get_ticket_bundle(self.ticket_id)


class UnixHTTPServer(socketserver.UnixStreamServer):
    allow_reuse_address = True


def make_handler(application: DemoTicketApplication) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "gaidemo-read-gateway"
        sys_version = ""

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            try:
                status, value = application.get(self.path)
            except ValueError as exc:
                status, value = 502, {"error": str(exc)}
            payload = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def serve(socket_path: Path) -> None:
    ticket_id_text = os.environ.get("DEMO_TICKET_ID", "").strip()
    if not ticket_id_text.isdecimal():
        raise ValueError("DEMO_TICKET_ID must be a positive integer")
    application = DemoTicketApplication(
        FreshworksClient(FreshworksConfig.from_environment()),
        int(ticket_id_text),
    )
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    socket_path.unlink(missing_ok=True)
    with UnixHTTPServer(str(socket_path), make_handler(application)) as server:
        socket_path.chmod(0o660)
        server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(prog="gaidemo-read-gateway")
    parser.add_argument("--socket", type=Path, required=True)
    args = parser.parse_args()
    serve(args.socket)


if __name__ == "__main__":
    main()
