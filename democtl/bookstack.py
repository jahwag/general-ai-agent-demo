from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

from .knowledge import CitationDetails


BOOKSTACK_CITATION = re.compile(
    r"^bookstack://pages/(?P<page_id>[1-9][0-9]*)@revision-(?P<revision>[1-9][0-9]*)$"
)


@dataclass(frozen=True)
class BookStackConfig:
    base_url: str
    token_id: str
    token_secret: str

    @classmethod
    def from_environment(cls) -> "BookStackConfig":
        base_url = os.environ.get("BOOKSTACK_BASE_URL", "").strip().rstrip("/")
        token_id = os.environ.get("BOOKSTACK_TOKEN_ID", "").strip()
        token_secret = os.environ.get("BOOKSTACK_TOKEN_SECRET", "").strip()
        parsed = urllib.parse.urlparse(base_url)
        is_loopback_http = parsed.scheme == "http" and parsed.hostname in {
            "127.0.0.1",
            "localhost",
            "::1",
        }
        if not (
            (parsed.scheme == "https" or is_loopback_http)
            and parsed.hostname
            and parsed.path in ("", "/")
            and not parsed.query
            and not parsed.fragment
        ):
            raise ValueError(
                "BOOKSTACK_BASE_URL must be an HTTPS origin or a loopback HTTP origin"
            )
        if not token_id or not token_secret:
            raise ValueError("BOOKSTACK_TOKEN_ID and BOOKSTACK_TOKEN_SECRET are required")
        if any(character.isspace() for character in token_id + token_secret):
            raise ValueError("BookStack API credentials must not contain whitespace")
        return cls(base_url=base_url, token_id=token_id, token_secret=token_secret)


class BookStackClient:
    def __init__(self, config: BookStackConfig) -> None:
        self.config = config

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> Any:
        if not path.startswith("/api/"):
            raise ValueError("BookStack client only permits API paths")
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.base_url}{path}",
            data=payload,
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": (
                    f"Token {self.config.token_id}:{self.config.token_secret}"
                ),
                "Content-Type": "application/json",
                "User-Agent": "general-ai-agent-demo/0.3",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status == 204:
                    return None
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise ValueError(f"BookStack API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ValueError(f"BookStack API request failed: {exc.reason}") from exc
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("BookStack API returned invalid JSON") from exc

    def search(self, query: str, *, count: int = 100) -> list[dict[str, Any]]:
        if not 1 <= count <= 100:
            raise ValueError("BookStack search count must be between 1 and 100")
        encoded = urllib.parse.urlencode({"query": query, "count": count})
        value = self._request("GET", f"/api/search?{encoded}")
        if not isinstance(value, dict) or not isinstance(value.get("data"), list):
            raise ValueError("BookStack search response did not contain a data list")
        return [item for item in value["data"] if isinstance(item, dict)]

    def get_page(self, page_id: int) -> dict[str, Any]:
        if page_id < 1:
            raise ValueError("BookStack page ID must be positive")
        value = self._request("GET", f"/api/pages/{page_id}")
        if not isinstance(value, dict):
            raise ValueError("BookStack page response was not an object")
        return value


class _PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _page_text(page: dict[str, Any]) -> str:
    markdown = page.get("markdown")
    if isinstance(markdown, str) and markdown.strip():
        return markdown
    raw_html = page.get("raw_html") or page.get("html")
    if not isinstance(raw_html, str):
        raise ValueError("BookStack page did not contain readable content")
    parser = _PlainTextParser()
    parser.feed(raw_html)
    return "\n".join(part.strip() for part in parser.parts if part.strip())


def _tag_value(page: dict[str, Any], name: str) -> str | None:
    tags = page.get("tags")
    if not isinstance(tags, list):
        return None
    for tag in tags:
        if not isinstance(tag, dict):
            continue
        if str(tag.get("name", "")).casefold() == name.casefold():
            value = tag.get("value")
            return value.strip() if isinstance(value, str) and value.strip() else None
    return None


class BookStackKnowledgeBase:
    def __init__(self, client: BookStackClient) -> None:
        self.client = client

    @classmethod
    def from_environment(cls) -> "BookStackKnowledgeBase":
        return cls(BookStackClient(BookStackConfig.from_environment()))

    def search(self, query: str, limit: int = 3) -> list[dict[str, object]]:
        if not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20")
        if not query.strip():
            raise ValueError("query must contain searchable text")
        results: list[dict[str, object]] = []
        for item in self.client.search(query):
            if item.get("type") != "page" or not isinstance(item.get("id"), int):
                continue
            page = self.client.get_page(item["id"])
            revision = page.get("revision_count")
            if not isinstance(revision, int) or revision < 1:
                raise ValueError("BookStack page revision was missing or invalid")
            details = self._details(page, revision)
            excerpt = " ".join(details.content.split())[:520]
            results.append(
                {
                    "citation": details.citation,
                    "title": details.title,
                    "source_url": details.source_url,
                    "revision": details.version,
                    "owner": details.owner,
                    "updated_at": details.updated_at,
                    "review_date": details.review_date,
                    "excerpt": excerpt,
                }
            )
            if len(results) == limit:
                break
        return results

    def citation_details(self, citation: str) -> CitationDetails:
        match = BOOKSTACK_CITATION.fullmatch(citation)
        if match is None:
            raise ValueError(f"unsupported citation: {citation}")
        page_id = int(match.group("page_id"))
        expected_revision = int(match.group("revision"))
        page = self.client.get_page(page_id)
        actual_revision = page.get("revision_count")
        if actual_revision != expected_revision:
            raise ValueError(
                f"BookStack page {page_id} changed from revision "
                f"{expected_revision} to {actual_revision}; search it again"
            )
        return self._details(page, expected_revision)

    def resolve_citation(self, citation: str) -> str:
        return self.citation_details(citation).content

    def _details(self, page: dict[str, Any], revision: int) -> CitationDetails:
        page_id = page.get("id")
        title = page.get("name")
        if not isinstance(page_id, int) or page_id < 1:
            raise ValueError("BookStack page ID was missing or invalid")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("BookStack page title was missing")
        owned_by = page.get("owned_by")
        api_owner = owned_by.get("name") if isinstance(owned_by, dict) else None
        owner = _tag_value(page, "Owner") or (
            api_owner.strip() if isinstance(api_owner, str) and api_owner.strip() else None
        )
        updated_at = page.get("updated_at")
        return CitationDetails(
            citation=f"bookstack://pages/{page_id}@revision-{revision}",
            content=_page_text(page),
            title=title.strip(),
            source_url=f"{self.client.config.base_url}/link/{page_id}",
            version=revision,
            owner=owner,
            updated_at=updated_at if isinstance(updated_at, str) else None,
            review_date=_tag_value(page, "Review due"),
        )
