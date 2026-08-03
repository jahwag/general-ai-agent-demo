from __future__ import annotations

import argparse
import json
import socketserver
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .bookstack import BookStackKnowledgeBase
from .proposal import ProposalError, validate_proposal


class KnowledgeApplication:
    """Read-only, query-scoped projection of the configured knowledge source."""

    def __init__(self, knowledge: BookStackKnowledgeBase) -> None:
        self.knowledge = knowledge

    def get(self, path: str) -> tuple[int, dict[str, object] | list[dict[str, object]]]:
        parsed = urlsplit(path)
        query = parse_qs(parsed.query, keep_blank_values=True)
        if parsed.path == "/api/demo/kb/search":
            search_text = query.get("query", [""])[0]
            limit_text = query.get("limit", ["3"])[0]
            if not limit_text.isdecimal():
                return 400, {"error": "limit must be a positive integer"}
            return 200, self.knowledge.search(search_text, limit=int(limit_text))
        if parsed.path == "/api/demo/kb/citation":
            citation = query.get("ref", [""])[0]
            if not citation:
                return 400, {"error": "ref is required"}
            return 200, asdict(self.knowledge.citation_details(citation))
        return 404, {"error": "knowledge endpoint not found"}

    def post(self, path: str, value: object) -> tuple[int, dict[str, object]]:
        parsed = urlsplit(path)
        if parsed.path != "/api/demo/kb/validate-proposal":
            return 404, {"error": "knowledge endpoint not found"}
        proposal = validate_proposal(value, self.knowledge)
        return 200, {
            "valid": True,
            "ticket_id": proposal["ticket_id"],
            "evidence": proposal["evidence"],
        }


class UnixHTTPServer(socketserver.UnixStreamServer):
    allow_reuse_address = True


def make_handler(application: KnowledgeApplication) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "gaidemo-knowledge-gateway"
        sys_version = ""

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            try:
                status, value = application.get(self.path)
            except ValueError as exc:
                status, value = 502, {"error": str(exc)}
            payload = json.dumps(
                value, ensure_ascii=False, sort_keys=True
            ).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 1 <= length <= 65536:
                    raise ProposalError("proposal body must be between 1 byte and 64 KiB")
                value = json.loads(self.rfile.read(length))
                status, result = application.post(self.path, value)
            except json.JSONDecodeError as exc:
                status, result = 400, {"error": f"proposal is not valid JSON: {exc}"}
            except ProposalError as exc:
                status, result = 422, {"error": str(exc)}
            except ValueError as exc:
                status, result = 502, {"error": str(exc)}
            payload = json.dumps(
                result, ensure_ascii=False, sort_keys=True
            ).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def serve(socket_path: Path) -> None:
    application = KnowledgeApplication(BookStackKnowledgeBase.from_environment())
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    socket_path.unlink(missing_ok=True)
    with UnixHTTPServer(str(socket_path), make_handler(application)) as server:
        socket_path.chmod(0o660)
        server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(prog="gaidemo-knowledge-gateway")
    parser.add_argument("--socket", type=Path, required=True)
    args = parser.parse_args()
    serve(args.socket)


if __name__ == "__main__":
    main()
