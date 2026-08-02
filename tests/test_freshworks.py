import unittest

from democtl.freshworks import FreshworksClient, FreshworksConfig


class StubFreshworksClient(FreshworksClient):
    def _request(self, method, path, body=None):  # type: ignore[no-untyped-def]
        self.last_request = (method, path, body)
        return {"tickets": [{"id": 1}]}


class StubConversationClient(FreshworksClient):
    def _request(self, method, path, body=None):  # type: ignore[no-untyped-def]
        return {
            "conversations": [
                {"id": 99, "user_id": 60000287482, "private": True}
            ]
        }


class StubTicketClient(FreshworksClient):
    def _request(self, method, path, body=None):  # type: ignore[no-untyped-def]
        return {"ticket": {"id": 1, "subject": "Synthetic ticket"}}


class StubMutationClient(FreshworksClient):
    def _request(self, method, path, body=None):  # type: ignore[no-untyped-def]
        if path.endswith("/notes"):
            return {"conversation": {"id": 10, "private": True}}
        return {"ticket": {"id": 1, "tags": ["human-approved"]}}


class FreshworksClientTests(unittest.TestCase):
    def test_auth_check_is_read_only_and_does_not_return_ticket_data(self) -> None:
        client = StubFreshworksClient(
            FreshworksConfig(
                base_url="https://example.freshservice.com",
                api_key="not-a-real-key",
                product="freshservice",
            )
        )

        result = client.check_authentication()

        self.assertEqual(client.last_request, ("GET", "/api/v2/tickets?per_page=1", None))
        self.assertEqual(
            result,
            {"authenticated": True, "product": "freshservice", "sample_count": 1},
        )

    def test_freshservice_conversation_wrapper_is_normalized(self) -> None:
        client = StubConversationClient(
            FreshworksConfig(
                base_url="https://example.freshservice.com",
                api_key="not-a-real-key",
                product="freshservice",
            )
        )

        conversations = client.get_conversations(1)

        self.assertEqual(
            conversations,
            [{"id": 99, "user_id": 60000287482, "private": True}],
        )

    def test_freshservice_ticket_wrapper_is_normalized(self) -> None:
        client = StubTicketClient(
            FreshworksConfig(
                base_url="https://example.freshservice.com",
                api_key="not-a-real-key",
                product="freshservice",
            )
        )

        ticket = client.get_ticket(1)

        self.assertEqual(ticket, {"id": 1, "subject": "Synthetic ticket"})

    def test_freshservice_mutation_wrappers_are_normalized(self) -> None:
        client = StubMutationClient(
            FreshworksConfig(
                base_url="https://example.freshservice.com",
                api_key="not-a-real-key",
                product="freshservice",
            )
        )

        note = client.add_private_note(1, "Approved note")
        ticket = client.update_ticket(1, {"tags": ["human-approved"]})

        self.assertEqual(note, {"id": 10, "private": True})
        self.assertEqual(ticket, {"id": 1, "tags": ["human-approved"]})


if __name__ == "__main__":
    unittest.main()
