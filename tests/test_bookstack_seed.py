import unittest

from democtl.bookstack_seed import _page_matches


class BookStackSeedTests(unittest.TestCase):
    def test_bookstack_normalization_does_not_create_fake_revision(self) -> None:
        desired_tags = [{"name": "Status", "value": "Approved"}]
        current = {
            "markdown": "Verified guidance.",
            "tags": [{"name": "Status", "value": "Approved", "order": 0}],
        }
        self.assertTrue(_page_matches(current, "Verified guidance.\n", desired_tags))

    def test_material_content_change_requires_revision(self) -> None:
        current = {"markdown": "Old guidance.", "tags": []}
        self.assertFalse(_page_matches(current, "New guidance.\n", []))


if __name__ == "__main__":
    unittest.main()
