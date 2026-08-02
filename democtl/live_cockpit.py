from __future__ import annotations

import argparse
import json
import os
import re
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .agentbus_client import AgentBusClient, AgentBusConfig, AgentBusError


HASH_RE = re.compile(r"^[0-9a-f]{64}$")
LOOPBACK_ORIGIN_RE = re.compile(r"^http://127\.0\.0\.1:[1-9][0-9]{0,4}$")


class CockpitState:
    def __init__(self, client: AgentBusClient, ticket_id: int) -> None:
        self.client = client
        self.ticket_id = ticket_id
        self.lock = threading.Lock()
        self.events: list[dict[str, Any]] = []
        self.proposal: dict[str, Any] | None = None
        self.approval: dict[str, Any] | None = None

    def add_message(self, message: dict[str, Any]) -> None:
        data = message.get("data")
        if not isinstance(data, dict):
            data = {}
        event = {
            "message_id": message.get("message_id"),
            "from": message.get("from"),
            "to": message.get("to"),
            "ts": message.get("ts"),
            "body": message.get("body"),
            "data": data,
            "reply_to": message.get("reply_to"),
        }
        with self.lock:
            self.events.append(event)
            self.events = self.events[-100:]
            if (
                data.get("kind") == "proposal_ready"
                and data.get("ticket_id") == self.ticket_id
                and isinstance(data.get("proposal_hash"), str)
                and HASH_RE.fullmatch(data["proposal_hash"])
            ):
                self.proposal = {
                    "ticket_id": self.ticket_id,
                    "proposal_hash": data["proposal_hash"],
                    "message_id": message.get("message_id"),
                    "category": data.get("category"),
                    "citations": data.get("citations", []),
                }

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "ticket_id": self.ticket_id,
                "events": list(self.events),
                "proposal": None if self.proposal is None else dict(self.proposal),
                "approval": None if self.approval is None else dict(self.approval),
            }

    def approve(self, value: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            proposal = None if self.proposal is None else dict(self.proposal)
            existing = None if self.approval is None else dict(self.approval)
        if proposal is None:
            raise ValueError("no live proposal is awaiting approval")
        if value != {
            "phrase": "APPROVE",
            "ticket_id": proposal["ticket_id"],
            "proposal_hash": proposal["proposal_hash"],
        }:
            raise ValueError("approval must exactly match the live ticket and proposal hash")
        if existing is not None:
            return existing
        body = f"APPROVE ticket={proposal['ticket_id']} proposal={proposal['proposal_hash']}"
        sent = self.client.send(
            to="approval-gateway",
            body=body,
            client_message_id=(
                f"ticket-{proposal['ticket_id']}-human-approval-"
                f"{proposal['proposal_hash'][:12]}"
            ),
            data={
                "kind": "human_approval",
                "ticket_id": proposal["ticket_id"],
                "proposal_hash": proposal["proposal_hash"],
                "phrase": "APPROVE",
            },
            reply_to=proposal["message_id"],
        )
        approval = {
            "message_id": sent["message_id"],
            "ticket_id": proposal["ticket_id"],
            "proposal_hash": proposal["proposal_hash"],
            "status": "sent_to_gateway",
        }
        self.add_message(
            {
                "message_id": sent["message_id"],
                "from": "human-approval-bridge",
                "to": "approval-gateway",
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "body": body,
                "data": {
                    "kind": "human_approval",
                    "ticket_id": proposal["ticket_id"],
                    "proposal_hash": proposal["proposal_hash"],
                },
                "reply_to": proposal["message_id"],
            }
        )
        with self.lock:
            self.approval = approval
        return approval


def consume(state: CockpitState, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            delivery = state.client.wait(timeout=10)
            if delivery is None:
                continue
            for message in delivery["messages"]:
                if isinstance(message, dict):
                    state.add_message(message)
            state.client.ack(delivery["delivery_id"])
        except AgentBusError:
            stop.wait(2)


def make_handler(state: CockpitState, html: bytes) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "gaidemo-live-cockpit"
        sys_version = ""

        def _json(self, status: int, value: dict[str, Any]) -> None:
            payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
                return
            if self.path == "/api/state":
                self._json(200, state.snapshot())
                return
            self._json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/approve":
                self._json(404, {"error": "not found"})
                return
            try:
                if self.headers.get_content_type() != "application/json":
                    raise ValueError("approval requires application/json")
                origin = self.headers.get("Origin", "")
                if not LOOPBACK_ORIGIN_RE.fullmatch(origin):
                    raise ValueError("approval requires the loopback cockpit origin")
                length = int(self.headers.get("Content-Length", "0"))
                if length < 2 or length > 4096:
                    raise ValueError("invalid request size")
                value = json.loads(self.rfile.read(length))
                if not isinstance(value, dict):
                    raise ValueError("approval body must be an object")
                result = state.approve(value)
            except (json.JSONDecodeError, ValueError, AgentBusError) as exc:
                self._json(400, {"error": str(exc)})
                return
            self._json(200, result)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(prog="gaidemo-live-cockpit")
    parser.add_argument("--listen", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    ticket_id = int(os.environ["DEMO_TICKET_ID"])
    client = AgentBusClient(
        AgentBusConfig(
            server=os.environ["AGENTBUS_SERVER"],
            token_file=Path(os.environ["AGENTBUS_HUMAN_TOKEN_FILE"]),
        )
    )
    html = Path(os.environ["GAIDEMO_COCKPIT_HTML"]).read_bytes()
    state = CockpitState(client, ticket_id)
    stop = threading.Event()
    consumer = threading.Thread(target=consume, args=(state, stop), daemon=True)
    consumer.start()
    server = ThreadingHTTPServer((args.listen, args.port), make_handler(state, html))

    def shutdown(_signum: int, _frame: object) -> None:
        stop.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    try:
        server.serve_forever()
    finally:
        stop.set()
        consumer.join(timeout=3)
        server.server_close()


if __name__ == "__main__":
    main()
