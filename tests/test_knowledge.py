from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from democtl.knowledge import KnowledgeBase


class KnowledgeBaseTests(unittest.TestCase):
    def test_search_prefers_title_matches(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.md").write_text("# Wi-Fi recovery\nmanaged device", encoding="utf-8")
            (root / "b.md").write_text("# Other\nWi-Fi recovery managed", encoding="utf-8")
            results = KnowledgeBase(root).search("wifi recovery")
            self.assertEqual(results[0]["citation"], "kb://a.md")

    def test_citation_rejects_traversal(self) -> None:
        with TemporaryDirectory() as directory:
            knowledge = KnowledgeBase(Path(directory))
            with self.assertRaises(ValueError):
                knowledge.resolve_citation("kb://../secret.md")


if __name__ == "__main__":
    unittest.main()
