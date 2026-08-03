from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


TOKEN = re.compile(r"[a-z0-9][a-z0-9_-]{2,}")


@dataclass(frozen=True)
class CitationDetails:
    citation: str
    content: str
    title: str
    source_url: str | None = None
    version: int | None = None
    owner: str | None = None
    updated_at: str | None = None
    review_date: str | None = None


class KnowledgeBase:
    def __init__(self, root: Path) -> None:
        self.root = root

    def articles(self) -> list[Path]:
        if not self.root.is_dir():
            raise ValueError(f"knowledge directory does not exist: {self.root}")
        return sorted(self.root.glob("*.md"))

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return set(TOKEN.findall(value.casefold()))

    def search(self, query: str, limit: int = 3) -> list[dict[str, object]]:
        if limit < 1 or limit > 20:
            raise ValueError("limit must be between 1 and 20")
        query_tokens = self._tokens(query)
        if not query_tokens:
            raise ValueError("query must contain at least one searchable token")
        matches: list[dict[str, object]] = []
        for path in self.articles():
            content = path.read_text(encoding="utf-8")
            lines = content.splitlines()
            title = next(
                (line.removeprefix("# ").strip() for line in lines if line.startswith("# ")),
                path.stem,
            )
            title_hits = len(query_tokens & self._tokens(title))
            body_hits = len(query_tokens & self._tokens(content))
            score = title_hits * 3 + body_hits
            if score == 0:
                continue
            excerpt = " ".join(line.strip() for line in lines if line.strip())[:360]
            matches.append(
                {
                    "citation": f"kb://{path.name}",
                    "title": title,
                    "score": score,
                    "excerpt": excerpt,
                }
            )
        matches.sort(key=lambda item: (-int(item["score"]), str(item["citation"])))
        return matches[:limit]

    def citation_details(self, citation: str) -> CitationDetails:
        if not citation.startswith("kb://"):
            raise ValueError(f"unsupported citation: {citation}")
        name = citation.removeprefix("kb://")
        if not name or Path(name).name != name or not name.endswith(".md"):
            raise ValueError(f"unsafe citation: {citation}")
        path = self.root / name
        if not path.is_file():
            raise ValueError(f"unknown citation: {citation}")
        content = path.read_text(encoding="utf-8")
        title = next(
            (
                line.removeprefix("# ").strip()
                for line in content.splitlines()
                if line.startswith("# ")
            ),
            path.stem,
        )
        return CitationDetails(
            citation=citation,
            content=content,
            title=title,
        )

    def resolve_citation(self, citation: str) -> str:
        return self.citation_details(citation).content
