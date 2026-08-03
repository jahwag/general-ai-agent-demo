import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from democtl.knowledge import KnowledgeBase
from democtl.proposal import (
    ProposalError,
    apply_proposal,
    load_and_validate_proposal,
    publish_private_note,
)


PROPOSAL_HASH = "a" * 64


class StubMutationClient:
    def __init__(
        self,
        updated_at: str,
        conversations: list[dict[str, object]] | None = None,
    ) -> None:
        self.updated_at = updated_at
        self.conversations = conversations or []
        self.calls: list[tuple[object, ...]] = []

    def get_ticket(self, ticket_id: int) -> dict[str, object]:
        self.calls.append(("get_ticket", ticket_id))
        return {"id": ticket_id, "updated_at": self.updated_at, "tags": []}

    def get_conversations(self, ticket_id: int) -> list[dict[str, object]]:
        self.calls.append(("get_conversations", ticket_id))
        return self.conversations

    def add_private_note(self, ticket_id: int, body: str) -> dict[str, object]:
        self.calls.append(("add_private_note", ticket_id, body))
        return {"id": 10}

    def update_ticket(
        self, ticket_id: int, body: dict[str, object]
    ) -> dict[str, object]:
        self.calls.append(("update_ticket", ticket_id, body))
        return {"id": ticket_id, **body}


def proposal() -> dict[str, object]:
    return {
        "ticket_id": 1,
        "ticket_updated_at": "analyzed-version",
        "summary": "summary",
        "category": "Identity and Access",
        "private_note": "Follow the managed-device re-enrollment steps.",
        "evidence": [
            {"citation": "kb://article.md", "quote": "Verified sentence."}
        ],
        "tags_to_add": ["ai-assisted", "human-approved"],
    }


class ProposalTests(unittest.TestCase):
    def test_quote_must_exist_in_cited_article(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            kb = root / "kb"
            kb.mkdir()
            (kb / "article.md").write_text(
                "# Article\nVerified sentence.", encoding="utf-8"
            )
            path = root / "proposal.json"
            value = proposal()
            value["evidence"] = [
                {"citation": "kb://article.md", "quote": "Invented sentence."}
            ]
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(ProposalError):
                load_and_validate_proposal(path, KnowledgeBase(kb))

    def test_stale_ticket_blocks_private_note(self) -> None:
        client = StubMutationClient("newer-version")
        with self.assertRaisesRegex(ProposalError, "ticket changed"):
            publish_private_note(  # type: ignore[arg-type]
                client,
                proposal(),
                proposal_hash=PROPOSAL_HASH,
            )
        self.assertEqual(
            [call[0] for call in client.calls],
            ["get_conversations", "get_ticket"],
        )

    def test_private_note_is_published_without_metadata_mutation(self) -> None:
        client = StubMutationClient("analyzed-version")
        result = publish_private_note(  # type: ignore[arg-type]
            client,
            proposal(),
            proposal_hash=PROPOSAL_HASH,
        )
        self.assertEqual(result["note_id"], 10)
        self.assertEqual(
            [call[0] for call in client.calls],
            ["get_conversations", "get_ticket", "add_private_note"],
        )
        note_html = str(client.calls[-1][2])
        self.assertIn("AI-generated private guidance", note_html)
        self.assertIn(PROPOSAL_HASH, note_html)
        self.assertNotIn("approved by human", note_html)

    def test_private_note_retry_reuses_matching_proposal_reference(self) -> None:
        client = StubMutationClient(
            "post-note-version",
            [
                {
                    "id": 44,
                    "private": True,
                    "incoming": False,
                    "body_text": f"Proposal reference: {PROPOSAL_HASH}",
                }
            ],
        )
        result = publish_private_note(  # type: ignore[arg-type]
            client,
            proposal(),
            proposal_hash=PROPOSAL_HASH,
        )
        self.assertTrue(result["already_exists"])
        self.assertEqual(result["note_id"], 44)
        self.assertEqual(client.calls, [("get_conversations", 1)])

    def test_native_approval_applies_only_metadata(self) -> None:
        client = StubMutationClient("approval-version")
        result = apply_proposal(  # type: ignore[arg-type]
            client,
            proposal(),
            expected_updated_at="approval-version",
        )
        self.assertEqual(result["approved_changes"], ["tags"])
        self.assertEqual(
            [call[0] for call in client.calls],
            ["get_ticket", "update_ticket"],
        )
        self.assertNotIn("add_private_note", [call[0] for call in client.calls])


if __name__ == "__main__":
    unittest.main()
