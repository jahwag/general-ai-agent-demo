import os
import unittest
from unittest.mock import patch

from democtl.bookstack import BookStackConfig, BookStackKnowledgeBase


PAGE = {
    "id": 7,
    "name": "Recover MFA after a phone replacement",
    "markdown": "Never request a password or a one-time code in a ticket.",
    "revision_count": 3,
    "updated_at": "2026-08-03T12:00:00.000000Z",
    "owned_by": {"id": 2, "name": "Demo Operator"},
    "tags": [
        {"name": "Owner", "value": "IT Service Desk"},
        {"name": "Review due", "value": "2026-11-03"},
    ],
}


class StubBookStackClient:
    def __init__(self) -> None:
        self.config = BookStackConfig(
            "http://127.0.0.1:6875", "token-id", "token-secret"
        )

    def search(self, query: str) -> list[dict[str, object]]:
        return [
            {"id": 1, "type": "book", "name": "Runbooks"},
            {"id": 7, "type": "page", "name": PAGE["name"]},
        ]

    def get_page(self, page_id: int) -> dict[str, object]:
        if page_id != 7:
            raise AssertionError(f"unexpected page ID {page_id}")
        return dict(PAGE)


class BookStackKnowledgeBaseTests(unittest.TestCase):
    def test_search_returns_revision_bound_governed_citation(self) -> None:
        knowledge = BookStackKnowledgeBase(StubBookStackClient())  # type: ignore[arg-type]
        result = knowledge.search("phone MFA", limit=1)[0]
        self.assertEqual(result["citation"], "bookstack://pages/7@revision-3")
        self.assertEqual(result["owner"], "IT Service Desk")
        self.assertEqual(result["review_date"], "2026-11-03")
        self.assertEqual(result["source_url"], "http://127.0.0.1:6875/link/7")

    def test_citation_fails_closed_after_page_revision_changes(self) -> None:
        client = StubBookStackClient()
        knowledge = BookStackKnowledgeBase(client)  # type: ignore[arg-type]
        client.get_page = lambda page_id: {**PAGE, "revision_count": 4}  # type: ignore[method-assign]
        with self.assertRaisesRegex(ValueError, "changed from revision 3 to 4"):
            knowledge.resolve_citation("bookstack://pages/7@revision-3")

    def test_environment_allows_loopback_http_only(self) -> None:
        values = {
            "BOOKSTACK_BASE_URL": "http://bookstack.example.invalid",
            "BOOKSTACK_TOKEN_ID": "id",
            "BOOKSTACK_TOKEN_SECRET": "secret",
        }
        with patch.dict(os.environ, values, clear=True):
            with self.assertRaisesRegex(ValueError, "HTTPS origin"):
                BookStackConfig.from_environment()


if __name__ == "__main__":
    unittest.main()
