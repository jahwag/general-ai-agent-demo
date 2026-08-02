import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from democtl.knowledge import KnowledgeBase
from democtl.proposal import ProposalError, load_and_validate_proposal


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


if __name__ == "__main__":
    unittest.main()
