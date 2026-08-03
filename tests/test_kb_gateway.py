import unittest

from democtl.kb_gateway import KnowledgeApplication
from democtl.knowledge import CitationDetails


class StubKnowledge:
    def search(self, query: str, limit: int = 3) -> list[dict[str, object]]:
        return [{"query": query, "limit": limit}]

    def citation_details(self, citation: str) -> CitationDetails:
        return CitationDetails(citation, "Verified sentence.", "Article")


class KnowledgeApplicationTests(unittest.TestCase):
    def test_search_is_query_scoped(self) -> None:
        application = KnowledgeApplication(StubKnowledge())  # type: ignore[arg-type]
        status, value = application.get(
            "/api/demo/kb/search?query=phone%20MFA&limit=2"
        )
        self.assertEqual(status, 200)
        self.assertEqual(value, [{"query": "phone MFA", "limit": 2}])

    def test_citation_endpoint_returns_content_and_metadata(self) -> None:
        application = KnowledgeApplication(StubKnowledge())  # type: ignore[arg-type]
        status, value = application.get(
            "/api/demo/kb/citation?ref=bookstack%3A%2F%2Fpages%2F7%40revision-3"
        )
        self.assertEqual(status, 200)
        self.assertEqual(value["content"], "Verified sentence.")

    def test_other_paths_do_not_expose_content(self) -> None:
        application = KnowledgeApplication(StubKnowledge())  # type: ignore[arg-type]
        status, _ = application.get("/api/demo/kb/pages")
        self.assertEqual(status, 404)

    def test_proposal_validation_uses_live_knowledge(self) -> None:
        application = KnowledgeApplication(StubKnowledge())  # type: ignore[arg-type]
        status, value = application.post(
            "/api/demo/kb/validate-proposal",
            {
                "ticket_id": 7,
                "ticket_updated_at": "2026-08-03T12:00:00Z",
                "summary": "Replacement phone needs MFA recovery.",
                "category": "Identity and Access",
                "private_note": "Follow the approved recovery runbook.",
                "evidence": [
                    {
                        "citation": "bookstack://pages/7@revision-3",
                        "quote": "Verified sentence.",
                    }
                ],
                "tags_to_add": ["ai-assisted"],
            },
        )
        self.assertEqual(status, 200)
        self.assertTrue(value["valid"])


if __name__ == "__main__":
    unittest.main()
