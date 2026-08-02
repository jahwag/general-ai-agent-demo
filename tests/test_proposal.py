import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from democtl.knowledge import KnowledgeBase
from democtl.proposal import ProposalError, apply_proposal, load_and_validate_proposal


class StubMutationClient:
    def __init__(self, updated_at: str) -> None:
        self.updated_at = updated_at
        self.calls: list[tuple[object, ...]] = []

    def get_ticket(self, ticket_id: int) -> dict[str, object]:
        self.calls.append(("get_ticket", ticket_id))
        return {"id": ticket_id, "updated_at": self.updated_at, "tags": []}

    def add_private_note(self, ticket_id: int, body: str) -> dict[str, object]:
        self.calls.append(("add_private_note", ticket_id, body))
        return {"id": 10}

    def update_ticket(self, ticket_id: int, body: dict[str, object]) -> dict[str, object]:
        self.calls.append(("update_ticket", ticket_id, body))
        return {"id": ticket_id, **body}


class ProposalTests(unittest.TestCase):
    def test_quote_must_exist_in_cited_article(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            kb = root / "kb"
            kb.mkdir()
            (kb / "article.md").write_text("# Article\nVerified sentence.", encoding="utf-8")
            proposal = root / "proposal.json"
            proposal.write_text(
                json.dumps(
                    {
                        "ticket_id": 1,
                        "ticket_updated_at": "now",
                        "summary": "summary",
                        "category": "category",
                        "private_note": "note",
                        "evidence": [
                            {"citation": "kb://article.md", "quote": "Invented sentence."}
                        ],
                        "tags_to_add": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ProposalError):
                load_and_validate_proposal(proposal, KnowledgeBase(kb))

    def test_stale_ticket_prevents_all_mutations(self) -> None:
        client = StubMutationClient("newer-version")
        proposal = {
            "ticket_id": 1,
            "ticket_updated_at": "analyzed-version",
            "private_note": "Synthetic note",
            "category": "Synthetic category",
            "evidence": [{"citation": "kb://article.md", "quote": "quote"}],
            "tags_to_add": ["human-approved"],
        }

        with self.assertRaisesRegex(ProposalError, "ticket changed"):
            apply_proposal(client, proposal)  # type: ignore[arg-type]

        self.assertEqual(client.calls, [("get_ticket", 1)])


if __name__ == "__main__":
    unittest.main()
