from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .freshworks import FreshworksClient
from .knowledge import KnowledgeBase


class ProposalError(ValueError):
    pass


def load_and_validate_proposal(
    path: Path, knowledge: KnowledgeBase
) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProposalError(f"proposal is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ProposalError("proposal must be a JSON object")
    required_text = ("ticket_updated_at", "summary", "category", "private_note")
    if not isinstance(value.get("ticket_id"), int) or value["ticket_id"] < 1:
        raise ProposalError("ticket_id must be a positive integer")
    for field in required_text:
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ProposalError(f"{field} must be a non-empty string")
    tags = value.get("tags_to_add", [])
    if not isinstance(tags, list) or any(
        not isinstance(tag, str) or not tag.strip() for tag in tags
    ):
        raise ProposalError("tags_to_add must be a list of non-empty strings")
    evidence = value.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ProposalError("evidence must contain at least one citation and quote")
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            raise ProposalError(f"evidence[{index}] must be an object")
        citation = item.get("citation")
        quote = item.get("quote")
        if not isinstance(citation, str) or not isinstance(quote, str) or not quote:
            raise ProposalError(f"evidence[{index}] requires citation and quote")
        article = knowledge.resolve_citation(citation)
        if " ".join(quote.split()).casefold() not in " ".join(article.split()).casefold():
            raise ProposalError(
                f"evidence[{index}] quote does not occur in {citation}"
            )
    return value


def _note_html(proposal: dict[str, Any]) -> str:
    evidence = "".join(
        f"<li><code>{html.escape(item['citation'])}</code>: "
        f"{html.escape(item['quote'])}</li>"
        for item in proposal["evidence"]
    )
    return (
        "<p><strong>AI-assisted draft approved by a human operator.</strong></p>"
        f"<p>{html.escape(proposal['private_note'])}</p>"
        f"<p><strong>Proposed category:</strong> "
        f"{html.escape(proposal['category'])}</p>"
        f"<p><strong>Knowledge evidence:</strong></p><ul>{evidence}</ul>"
    )


def apply_proposal(
    client: FreshworksClient,
    proposal: dict[str, Any],
    *,
    expected_updated_at: str | None = None,
) -> dict[str, Any]:
    current = client.get_ticket(proposal["ticket_id"])
    expected = expected_updated_at or proposal["ticket_updated_at"]
    if current.get("updated_at") != expected:
        raise ProposalError(
            "ticket changed after analysis; fetch it again before approval"
        )
    note = client.add_private_note(proposal["ticket_id"], _note_html(proposal))
    current_tags = [str(tag) for tag in current.get("tags") or []]
    merged_tags = sorted(set(current_tags + proposal.get("tags_to_add", [])))
    updated = client.update_ticket(proposal["ticket_id"], {"tags": merged_tags})
    return {
        "applied": True,
        "ticket_id": proposal["ticket_id"],
        "note_id": note.get("id"),
        "tags": updated.get("tags", merged_tags),
    }
