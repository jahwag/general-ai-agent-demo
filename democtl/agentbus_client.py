from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class AgentBusError(ValueError):
    pass


@dataclass(frozen=True)
class AgentBusConfig:
    server: str
    token_file: Path


class AgentBusClient:
    def __init__(self, config: AgentBusConfig) -> None:
        server = config.server.rstrip("/")
        if not server.startswith("http://127.0.0.1:"):
            raise AgentBusError("demo AgentBus must use loopback HTTP")
        token = config.token_file.read_text(encoding="utf-8").strip()
        if not token or any(character.isspace() for character in token):
            raise AgentBusError("AgentBus token file was empty or invalid")
        self.server = server
        self.token = token

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        timeout: float = 30,
    ) -> dict[str, Any] | None:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.server}{path}",
            data=payload,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "general-ai-agent-demo/0.2",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status == 204:
                    return None
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise AgentBusError(f"AgentBus HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise AgentBusError(f"AgentBus request failed: {exc.reason}") from exc
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AgentBusError("AgentBus returned invalid JSON") from exc
        if not isinstance(value, dict):
            raise AgentBusError("AgentBus returned a non-object response")
        return value

    def send(
        self,
        *,
        to: str,
        body: str,
        client_message_id: str,
        data: dict[str, Any] | None = None,
        reply_to: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "to": to,
            "body": body,
            "client_message_id": client_message_id,
        }
        if data is not None:
            payload["data"] = data
        if reply_to is not None:
            payload["reply_to"] = reply_to
        response = self._request("POST", "/send", payload)
        if response is None or not isinstance(response.get("message_id"), str):
            raise AgentBusError("AgentBus send response lacked message_id")
        return response

    def wait(self, *, timeout: float = 20) -> dict[str, Any] | None:
        query = urllib.parse.urlencode({"timeout": str(timeout)})
        response = self._request("GET", f"/wait?{query}", timeout=timeout + 5)
        if response is None:
            return None
        if not isinstance(response.get("delivery_id"), str):
            raise AgentBusError("AgentBus delivery lacked delivery_id")
        if not isinstance(response.get("messages"), list):
            raise AgentBusError("AgentBus delivery lacked messages")
        return response

    def ack(self, delivery_id: str) -> None:
        response = self._request("POST", "/ack", {"delivery_id": delivery_id})
        if response is None or response.get("acked") is not True:
            raise AgentBusError("AgentBus acknowledgement failed")
