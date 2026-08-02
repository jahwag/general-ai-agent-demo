import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from democtl.approval_gateway import process_message
from democtl.live_cockpit import CockpitState, make_handler


class FakeClient:
    def __init__(self) -> None:
        self.sent = []

    def send(self, **value):  # type: ignore[no-untyped-def]
        self.sent.append(value)
        return {"message_id": "msg_approval123"}


class LivePromptTests(unittest.TestCase):
    def test_intake_example_does_not_emit_placeholder_body(self) -> None:
        root = Path(__file__).resolve().parents[1]
        prompt = (root / "CLAUDE.shared.md").read_text(encoding="utf-8")

        self.assertNotIn("-intake BODY ", prompt)
        self.assertIn("run-RUN_ID-intake", prompt)
        self.assertIn("I picked up Freshservice ticket TICKET_ID", prompt)

    def test_cockpit_and_gateway_have_separate_os_identities(self) -> None:
        root = Path(__file__).resolve().parents[1]
        cockpit = (root / "infra/systemd/gaidemo-live-cockpit.service").read_text()
        gateway = (root / "infra/systemd/gaidemo-agentbus-approval.service").read_text()
        installer = (root / "infra/install-agentbus-demo.sh").read_text()

        self.assertIn("User=gaidemo-human", cockpit)
        self.assertIn("EnvironmentFile=/etc/gaidemo-human/cockpit.env", cockpit)
        self.assertIn("User=gaidemo-operator", gateway)
        self.assertIn("EnvironmentFile=/etc/gaidemo/agentbus.env", gateway)
        self.assertIn("/var/lib/gaidemo-human/agentbus.token", installer)
        self.assertNotIn("AGENTBUS_HUMAN_TOKEN_FILE=/var/lib/gaidemo-operator", installer)


class LiveCockpitTests(unittest.TestCase):
    def test_approval_endpoint_rejects_missing_browser_origin(self) -> None:
        client = FakeClient()
        state = CockpitState(client, 2)  # type: ignore[arg-type]
        proposal_hash = "b" * 64
        state.add_message(
            {
                "message_id": "msg_proposal456",
                "from": "cora",
                "data": {
                    "kind": "proposal_ready",
                    "ticket_id": 2,
                    "proposal_hash": proposal_hash,
                },
            }
        )
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), make_handler(state, b"<html></html>")
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            value = {
                "phrase": "APPROVE",
                "ticket_id": 2,
                "proposal_hash": proposal_hash,
            }
            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_port}/api/approve",
                data=json.dumps(value).encode("utf-8"),
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(request, timeout=2)
            self.assertEqual(raised.exception.code, 400)
            self.assertEqual(client.sent, [])
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    def test_exact_live_proposal_can_be_approved_once(self) -> None:
        client = FakeClient()
        state = CockpitState(client, 2)  # type: ignore[arg-type]
        proposal_hash = "a" * 64
        state.add_message(
            {
                "message_id": "msg_proposal123",
                "from": "cora",
                "to": "human-approval-bridge",
                "body": "Proposal ready",
                "data": {
                    "kind": "proposal_ready",
                    "ticket_id": 2,
                    "proposal_hash": proposal_hash,
                    "category": "Identity and Access",
                },
            }
        )
        value = {
            "phrase": "APPROVE",
            "ticket_id": 2,
            "proposal_hash": proposal_hash,
        }
        first = state.approve(value)
        second = state.approve(value)
        self.assertEqual(first, second)
        self.assertEqual(len(client.sent), 1)
        self.assertEqual(client.sent[0]["to"], "approval-gateway")
        self.assertEqual(client.sent[0]["data"]["kind"], "human_approval")

    def test_approval_must_match_exact_proposal(self) -> None:
        client = FakeClient()
        state = CockpitState(client, 2)  # type: ignore[arg-type]
        state.add_message(
            {
                "message_id": "msg_proposal123",
                "from": "cora",
                "to": "human-approval-bridge",
                "body": "Proposal ready",
                "data": {
                    "kind": "proposal_ready",
                    "ticket_id": 2,
                    "proposal_hash": "a" * 64,
                },
            }
        )
        with self.assertRaisesRegex(ValueError, "exactly match"):
            state.approve(
                {
                    "phrase": "approve",
                    "ticket_id": 2,
                    "proposal_hash": "a" * 64,
                }
            )
        self.assertEqual(client.sent, [])

    def test_gateway_ignores_non_human_sender_without_mutation(self) -> None:
        client = FakeClient()
        with tempfile.TemporaryDirectory() as directory:
            accepted = process_message(
                client,  # type: ignore[arg-type]
                {
                    "message_id": "msg_untrusted123",
                    "from": "cora",
                    "body": f"APPROVE ticket=2 proposal={'a' * 64}",
                    "data": {
                        "kind": "human_approval",
                        "phrase": "APPROVE",
                        "ticket_id": 2,
                        "proposal_hash": "a" * 64,
                    },
                },
                ticket_id=2,
                proposal_path=Path(directory) / "missing.json",
                state_dir=Path(directory),
            )
        self.assertTrue(accepted)
        self.assertEqual(client.sent, [])


if __name__ == "__main__":
    unittest.main()
