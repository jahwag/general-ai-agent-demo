import unittest

from democtl.read_gateway import DemoTicketApplication


class StubClient:
    def get_ticket_bundle(self, ticket_id: int) -> dict[str, object]:
        return {"ticket": {"id": ticket_id}, "conversations": []}


class DemoTicketApplicationTests(unittest.TestCase):
    def test_returns_only_the_configured_ticket(self) -> None:
        application = DemoTicketApplication(StubClient(), 7)  # type: ignore[arg-type]

        status, body = application.get("/api/demo/tickets/7")

        self.assertEqual(status, 200)
        self.assertEqual(body["ticket"], {"id": 7})

    def test_rejects_ticket_enumeration(self) -> None:
        application = DemoTicketApplication(StubClient(), 7)  # type: ignore[arg-type]

        status, body = application.get("/api/demo/tickets/8")

        self.assertEqual(status, 404)
        self.assertEqual(body, {"error": "demo ticket not found"})


if __name__ == "__main__":
    unittest.main()
