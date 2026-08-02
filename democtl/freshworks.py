from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FreshworksConfig:
    base_url: str
    api_key: str
    product: str

    @classmethod
    def from_environment(cls) -> "FreshworksConfig":
        base_url = os.environ.get("FRESHWORKS_BASE_URL", "").strip().rstrip("/")
        api_key = os.environ.get("FRESHWORKS_API_KEY", "").strip()
        product = os.environ.get("FRESHWORKS_PRODUCT", "freshservice").strip()
        if not base_url.startswith("https://"):
            raise ValueError("FRESHWORKS_BASE_URL must be an https:// tenant URL")
        parsed = urllib.parse.urlparse(base_url)
        if parsed.path not in ("", "/") or not parsed.hostname:
            raise ValueError("FRESHWORKS_BASE_URL must not contain a path")
        if not api_key:
            raise ValueError("FRESHWORKS_API_KEY is required")
        if product not in {"freshservice", "freshdesk"}:
            raise ValueError("FRESHWORKS_PRODUCT must be freshservice or freshdesk")
        return cls(base_url=base_url, api_key=api_key, product=product)


class FreshworksClient:
    def __init__(self, config: FreshworksConfig) -> None:
        self.config = config

    def _request(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> Any:
        token = base64.b64encode(
            f"{self.config.api_key}:X".encode("utf-8")
        ).decode("ascii")
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.base_url}{path}",
            data=payload,
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {token}",
                "Content-Type": "application/json",
                "User-Agent": "general-ai-agent-demo/0.1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
                return {} if not raw else json.loads(raw)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise ValueError(
                f"Freshworks API returned HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ValueError(f"Freshworks API request failed: {exc.reason}") from exc

    def get_ticket(self, ticket_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v2/tickets/{ticket_id}")

    def get_conversations(self, ticket_id: int) -> list[dict[str, Any]]:
        value = self._request("GET", f"/api/v2/tickets/{ticket_id}/conversations")
        if not isinstance(value, list):
            raise ValueError("Freshworks conversations response was not a list")
        return value

    def get_ticket_bundle(self, ticket_id: int) -> dict[str, Any]:
        ticket = self.get_ticket(ticket_id)
        conversations = self.get_conversations(ticket_id)
        ticket_fields = (
            "id",
            "subject",
            "description_text",
            "status",
            "priority",
            "type",
            "category",
            "sub_category",
            "item_category",
            "tags",
            "created_at",
            "updated_at",
        )
        conversation_fields = (
            "id",
            "incoming",
            "private",
            "body_text",
            "created_at",
            "updated_at",
        )
        return {
            "ticket": {key: ticket.get(key) for key in ticket_fields},
            "conversations": [
                {key: item.get(key) for key in conversation_fields}
                for item in conversations
            ],
        }

    def create_ticket(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v2/tickets", body)

    def add_private_note(self, ticket_id: int, body: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/v2/tickets/{ticket_id}/notes",
            {"body": body, "private": True},
        )

    def update_ticket(self, ticket_id: int, body: dict[str, Any]) -> dict[str, Any]:
        return self._request("PUT", f"/api/v2/tickets/{ticket_id}", body)

