import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from democtl.ticket_fixture import load_synthetic_ticket


class TicketFixtureTests(unittest.TestCase):
    def write_fixture(self, directory: str, **overrides: object) -> Path:
        value: dict[str, object] = {
            "email": "alex.taylor@example.invalid",
            "subject": "Synthetic access problem",
            "description": "This ticket contains synthetic demo data.",
            "priority": 2,
            "status": 2,
            "tags": ["synthetic-ai-demo"],
        }
        value.update(overrides)
        path = Path(directory) / "ticket.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_accepts_safe_synthetic_fixture(self) -> None:
        with TemporaryDirectory() as directory:
            ticket = load_synthetic_ticket(self.write_fixture(directory))
        self.assertEqual(ticket["email"], "alex.taylor@example.invalid")

    def test_rejects_non_reserved_email_domain(self) -> None:
        with TemporaryDirectory() as directory:
            path = self.write_fixture(directory, email="real.person@example.com")
            with self.assertRaisesRegex(ValueError, r"reserved \.invalid domain"):
                load_synthetic_ticket(path)

    def test_rejects_fixture_without_synthetic_tag(self) -> None:
        with TemporaryDirectory() as directory:
            path = self.write_fixture(directory, tags=["not-a-demo"])
            with self.assertRaisesRegex(ValueError, "synthetic-ai-demo"):
                load_synthetic_ticket(path)

    def test_rejects_fields_outside_write_allowlist(self) -> None:
        with TemporaryDirectory() as directory:
            path = self.write_fixture(directory, responder_id=123)
            with self.assertRaisesRegex(ValueError, "unsupported fields"):
                load_synthetic_ticket(path)


if __name__ == "__main__":
    unittest.main()
