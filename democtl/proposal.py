from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from .freshworks import FreshworksClient
from .knowledge import KnowledgeBase


STALE_TICKET_ERROR = "ticket changed after analysis; fetch it again before action"
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


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
        if " ".join(quote.split()).casefold() not in " ".join(
            article.split()
        ).casefold():
            raise ProposalError(
                f"evidence[{index}] quote does not occur in {citation}"
            )
    return value


def _note_html(proposal: dict[str, Any], proposal_hash: str) -> str:
    evidence = "".join(
        f"<li><code>{html.escape(item['citation'])}</code>: "
        f"{html.escape(item['quote'])}</li>"
        for item in proposal["evidence"]
    )
    return (
        "<p><strong>AI-generated private guidance for operator review. "
        "No ticket fields were changed.</strong></p>"
        f"<p>{html.escape(proposal['private_note'])}</p>"
        "<p><strong>Recommended category:</strong> "
        f"{html.escape(proposal['category'])}</p>"
        f"<p><strong>Knowledge evidence:</strong></p><ul>{evidence}</ul>"
        f"<p><small>Proposal reference: <code>{proposal_hash}</code></small></p>"
    )


def _current_ticket(
    client: FreshworksClient,
    proposal: dict[str, Any],
    expected_updated_at: str | None,
) -> dict[str, Any]:
    current = client.get_ticket(proposal["ticket_id"])
    expected = expected_updated_at or proposal["ticket_updated_at"]
    if current.get("updated_at") != expected:
        raise ProposalError(STALE_TICKET_ERROR)
    return current


def publish_private_note(
    client: FreshworksClient,
    proposal: dict[str, Any],
    *,
    proposal_hash: str,
    expected_updated_at: str | None = None,
) -> dict[str, Any]:
    """Publish one internal note without applying approval-gated ticket fields."""

    if not HASH_RE.fullmatch(proposal_hash):
        raise ProposalError("proposal hash is invalid")
    for conversation in client.get_conversations(proposal["ticket_id"]):
        if (
            conversation.get("private") is True
            and conversation.get("incoming") is False
            and proposal_hash in str(conversation.get("body_text") or "")
        ):
            return {
                "published": True,
                "already_exists": True,
                "ticket_id": proposal["ticket_id"],
                "note_id": conversation.get("id"),
                "ticket_updated_at_before": proposal["ticket_updated_at"],
            }
    current = _current_ticket(client, proposal, expected_updated_at)
    note = client.add_private_note(
        proposal["ticket_id"], _note_html(proposal, proposal_hash)
    )
    return {
        "published": True,
        "ticket_id": proposal["ticket_id"],
        "note_id": note.get("id"),
        "ticket_updated_at_before": current.get("updated_at"),
    }


def apply_proposal(
    client: FreshworksClient,
    proposal: dict[str, Any],
    *,
    expected_updated_at: str | None = None,
) -> dict[str, Any]:
    """Apply only the ticket metadata covered by explicit human approval."""

    current = _current_ticket(client, proposal, expected_updated_at)
    current_tags = [str(tag) for tag in current.get("tags") or []]
    merged_tags = sorted(set(current_tags + proposal.get("tags_to_add", [])))
    if merged_tags == sorted(set(current_tags)):
        updated = current
    else:
        updated = client.update_ticket(proposal["ticket_id"], {"tags": merged_tags})
    return {
        "applied": True,
        "ticket_id": proposal["ticket_id"],
        "approved_changes": ["tags"],
        "tags": updated.get("tags", merged_tags),
    }
