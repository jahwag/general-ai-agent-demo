import json
import hashlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from democtl.approval_gateway import process_message
from democtl.live_cockpit import CockpitState, make_handler
from democtl.native_approval import (
    NativeApprovalError,
    approval_command,
    detect_native_approval,
    publish_native_approval,
)


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

    def test_cockpit_approver_and_gateway_have_separate_identities(self) -> None:
        root = Path(__file__).resolve().parents[1]
        cockpit = (root / "infra/systemd/gaidemo-live-cockpit.service").read_text()
        approver = (
            root / "infra/systemd/gaidemo-freshservice-approval.service"
        ).read_text()
        gateway = (root / "infra/systemd/gaidemo-agentbus-approval.service").read_text()
        installer = (root / "infra/install-agentbus-demo.sh").read_text()

        self.assertIn("User=gaidemo-human", cockpit)
        self.assertIn("EnvironmentFile=/etc/gaidemo-human/cockpit.env", cockpit)
        self.assertIn("User=gaidemo-approver", approver)
        self.assertIn(
            "EnvironmentFile=/etc/gaidemo-approver/approval.env", approver
        )
        self.assertIn("ReadOnlyPaths=/var/lib/gaidemo-human", approver)
        self.assertIn("ReadWritePaths=/var/lib/gaidemo-approver", approver)
        self.assertIn("User=gaidemo-operator", gateway)
        self.assertIn("EnvironmentFile=/etc/gaidemo/agentbus.env", gateway)
        self.assertIn("/var/lib/gaidemo-human/agentbus.token", installer)
        self.assertIn("/var/lib/gaidemo-approver/agentbus.token", installer)
        self.assertIn("freshservice-approval-bridge", installer)
        self.assertIn("proposal_group=gaidemo-proposals", installer)
        self.assertIn('chmod 0640 "$proposal_path"', installer)
        self.assertNotIn("AGENTBUS_HUMAN_TOKEN_FILE=/var/lib/gaidemo-operator", installer)

    def test_main_cockpit_collapses_internal_principals_into_product_actors(self) -> None:
        root = Path(__file__).resolve().parents[1]
        html = (root / "democtl/live_cockpit.html").read_text(encoding="utf-8")

        self.assertIn("Cora · approved action", html)
        self.assertIn("Human operator", html)
        self.assertIn("Safety guard", html)
        self.assertIn("AgentBus principal:", html)
        self.assertNotIn('"Operator gateway"', html)


class LiveCockpitTests(unittest.TestCase):
    def test_approval_endpoint_redirects_operator_to_freshservice(self) -> None:
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
            self.assertEqual(raised.exception.code, 410)
            self.assertEqual(client.sent, [])
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    def test_proposal_descriptor_is_persisted_for_native_approval(self) -> None:
        client = FakeClient()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "current-proposal.json"
            state = CockpitState(client, 2, path)  # type: ignore[arg-type]
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
                        "ticket_updated_at": "analyzed-version",
                        "category": "Identity and Access",
                    },
                }
            )
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["proposal_hash"], "a" * 64)
        self.assertEqual(saved["approval_command"], f"APPROVE AI {'a' * 12}")

    def test_cockpit_cannot_emit_approval(self) -> None:
        client = FakeClient()
        state = CockpitState(client, 2)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "private note in Freshservice"):
            state.approve({})
        self.assertEqual(client.sent, [])

    def test_only_native_watcher_can_mark_human_approval(self) -> None:
        client = FakeClient()
        state = CockpitState(client, 2)  # type: ignore[arg-type]
        data = {
            "kind": "approval_verified",
            "ticket_id": 2,
            "proposal_hash": "d" * 64,
        }
        state.add_message(
            {
                "message_id": "msg_untrusted_approval",
                "from": "cora",
                "body": "not trusted",
                "data": data,
            }
        )
        self.assertIsNone(state.snapshot()["approval"])

        state.add_message(
            {
                "message_id": "msg_native_approval",
                "from": "freshservice-approval-bridge",
                "body": "Human approval verified",
                "data": data,
            }
        )
        self.assertEqual(
            state.snapshot()["approval"]["status"], "verified_in_freshservice"
        )

    def test_gateway_ignores_cockpit_sender_without_mutation(self) -> None:
        client = FakeClient()
        with tempfile.TemporaryDirectory() as directory:
            accepted = process_message(
                client,  # type: ignore[arg-type]
                {
                    "message_id": "msg_untrusted123",
                    "from": "human-approval-bridge",
                    "body": f"APPROVE ticket=2 proposal={'a' * 64}",
                    "data": {
                        "kind": "human_approval",
                        "phrase": "APPROVE",
                        "ticket_id": 2,
                        "proposal_hash": "a" * 64,
                    },
                },
                ticket_id=2,
                trusted_operator_id=60000287482,
                proposal_path=Path(directory) / "missing.json",
                state_dir=Path(directory),
            )
            self.assertTrue(accepted)
            self.assertEqual(client.sent, [])

    @mock.patch("democtl.approval_gateway.subprocess.run")
    def test_gateway_executes_only_trusted_native_approval(
        self, run: mock.Mock
    ) -> None:
        client = FakeClient()
        run.return_value = mock.Mock(
            returncode=0,
            stdout=json.dumps(
                {"ticket_id": 2, "note_id": 77, "tags": ["human-approved"]}
            ),
            stderr="",
        )
        with tempfile.TemporaryDirectory() as directory:
            proposal_path = Path(directory) / "proposal.json"
            proposal_path.write_text(
                json.dumps({"ticket_id": 2, "private_note": "Synthetic note"}),
                encoding="utf-8",
            )
            state_dir = Path(directory) / "state"
            state_dir.mkdir()
            proposal_hash = hashlib.sha256(proposal_path.read_bytes()).hexdigest()
            message = {
                "message_id": "msg_native_approval",
                "from": "freshservice-approval-bridge",
                "body": f"APPROVE ticket=2 proposal={proposal_hash}",
                "data": {
                    "kind": "human_approval",
                    "phrase": "APPROVE",
                    "source": "freshservice_private_note",
                    "ticket_id": 2,
                    "proposal_hash": proposal_hash,
                    "operator_user_id": 60000287482,
                    "approval_conversation_id": 44,
                    "ticket_updated_at": "approval-version",
                },
            }

            accepted = process_message(
                client,  # type: ignore[arg-type]
                message,
                ticket_id=2,
                trusted_operator_id=60000287482,
                proposal_path=proposal_path,
                state_dir=state_dir,
            )

        self.assertTrue(accepted)
        run.assert_called_once_with(
            [
                "/usr/local/bin/gaidemo-proposal-apply",
                "APPROVE",
                "approval-version",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )
        self.assertEqual(
            [sent["to"] for sent in client.sent],
            ["human-approval-bridge", "cora"],
        )

    @mock.patch("democtl.approval_gateway.subprocess.run")
    def test_gateway_acknowledges_and_audits_permanent_stale_rejection(
        self, run: mock.Mock
    ) -> None:
        client = FakeClient()
        run.return_value = mock.Mock(
            returncode=2,
            stdout=json.dumps(
                {
                    "error": (
                        "ticket changed after analysis; fetch it again before approval"
                    )
                }
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            proposal_path = Path(directory) / "proposal.json"
            proposal_path.write_text(
                json.dumps({"ticket_id": 2}),
                encoding="utf-8",
            )
            state_dir = Path(directory) / "state"
            state_dir.mkdir()
            proposal_hash = hashlib.sha256(proposal_path.read_bytes()).hexdigest()
            message = {
                "message_id": "msg_native_stale",
                "from": "freshservice-approval-bridge",
                "body": f"APPROVE ticket=2 proposal={proposal_hash}",
                "data": {
                    "kind": "human_approval",
                    "phrase": "APPROVE",
                    "source": "freshservice_private_note",
                    "ticket_id": 2,
                    "proposal_hash": proposal_hash,
                    "operator_user_id": 60000287482,
                    "approval_conversation_id": 44,
                    "ticket_updated_at": "stale-version",
                },
            }

            accepted = process_message(
                client,  # type: ignore[arg-type]
                message,
                ticket_id=2,
                trusted_operator_id=60000287482,
                proposal_path=proposal_path,
                state_dir=state_dir,
            )

            self.assertTrue(accepted)
            self.assertFalse((state_dir / f"2-{proposal_hash}.json").exists())
            self.assertEqual(
                [sent["to"] for sent in client.sent],
                ["cora"],
            )
            self.assertEqual(client.sent[0]["data"]["kind"], "apply_rejected")
            self.assertEqual(
                client.sent[0]["data"]["reason"],
                "ticket_version_changed",
            )


class NativeApprovalTests(unittest.TestCase):
    def test_publishes_visible_audit_before_gateway_approval(self) -> None:
        client = FakeClient()
        proposal_hash = "e" * 64
        approval = {
            "ticket_id": 2,
            "proposal_hash": proposal_hash,
            "proposal_message_id": "msg_proposal789",
            "approval_conversation_id": 44,
            "operator_user_id": 60000287482,
            "ticket_updated_at": "approval-version",
        }

        result = publish_native_approval(  # type: ignore[arg-type]
            client,
            2,
            approval,
        )

        self.assertEqual(
            [message["to"] for message in client.sent],
            ["human-approval-bridge", "approval-gateway"],
        )
        self.assertEqual(client.sent[0]["data"]["kind"], "approval_verified")
        self.assertEqual(client.sent[0]["reply_to"], "msg_proposal789")
        self.assertEqual(client.sent[1]["data"]["kind"], "human_approval")
        self.assertEqual(client.sent[1]["data"]["source"], "freshservice_private_note")
        self.assertEqual(
            client.sent[1]["body"],
            f"APPROVE ticket=2 proposal={proposal_hash}",
        )
        self.assertEqual(result["message_id"], "msg_approval123")
        self.assertEqual(result["audit_message_id"], "msg_approval123")
        self.assertTrue(client.sent[0]["client_message_id"].endswith("-44"))
        self.assertTrue(client.sent[1]["client_message_id"].endswith("-44"))

    proposal = {
        "ticket_id": 2,
        "proposal_hash": "c" * 64,
        "ticket_updated_at": "analyzed-version",
        "message_id": "msg_proposal789",
    }

    @staticmethod
    def bundle(
        *,
        conversations=None,
        updated_at="analyzed-version",
        status=2,
        responder_id=60000287482,
    ):
        return {
            "ticket": {
                "id": 2,
                "subject": "Synthetic ticket",
                "status": status,
                "responder_id": responder_id,
                "tags": ["synthetic-ai-demo"],
                "updated_at": updated_at,
            },
            "conversations": conversations or [],
        }

    def test_exact_trusted_private_note_becomes_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.json"
            self.assertIsNone(
                detect_native_approval(
                    self.proposal,
                    self.bundle(),
                    trusted_operator_id=60000287482,
                    baseline_path=baseline,
                )
            )
            approval = detect_native_approval(
                self.proposal,
                self.bundle(
                    updated_at="approval-version",
                    conversations=[
                        {
                            "id": 44,
                            "user_id": 60000287482,
                            "private": True,
                            "incoming": False,
                            "body_text": approval_command("c" * 64),
                        }
                    ],
                ),
                trusted_operator_id=60000287482,
                baseline_path=baseline,
            )
        self.assertEqual(approval["approval_conversation_id"], 44)
        self.assertEqual(approval["ticket_updated_at"], "approval-version")

    def test_approval_note_before_baseline_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.json"
            with self.assertRaisesRegex(NativeApprovalError, "before"):
                detect_native_approval(
                    self.proposal,
                    self.bundle(
                        updated_at="approval-version",
                        conversations=[
                            {
                                "id": 44,
                                "user_id": 60000287482,
                                "private": True,
                                "incoming": False,
                                "body_text": approval_command("c" * 64),
                            }
                        ],
                    ),
                    trusted_operator_id=60000287482,
                    baseline_path=baseline,
                )
            self.assertFalse(baseline.exists())

    def test_approval_note_waits_for_freshservice_ticket_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.json"
            detect_native_approval(
                self.proposal,
                self.bundle(),
                trusted_operator_id=60000287482,
                baseline_path=baseline,
            )

            self.assertIsNone(
                detect_native_approval(
                    self.proposal,
                    self.bundle(
                        updated_at="analyzed-version",
                        conversations=[
                            {
                                "id": 44,
                                "user_id": 60000287482,
                                "private": True,
                                "incoming": False,
                                "body_text": approval_command("c" * 64),
                            }
                        ],
                    ),
                    trusted_operator_id=60000287482,
                    baseline_path=baseline,
                )
            )

    def test_note_from_wrong_agent_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.json"
            detect_native_approval(
                self.proposal,
                self.bundle(),
                trusted_operator_id=60000287482,
                baseline_path=baseline,
            )
            with self.assertRaisesRegex(NativeApprovalError, "trusted approval"):
                detect_native_approval(
                    self.proposal,
                    self.bundle(
                        conversations=[
                            {
                                "id": 45,
                                "user_id": 7,
                                "private": True,
                                "incoming": False,
                                "body_text": approval_command("c" * 64),
                            }
                        ]
                    ),
                    trusted_operator_id=60000287482,
                    baseline_path=baseline,
                )

    def test_ticket_change_outside_note_workflow_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.json"
            detect_native_approval(
                self.proposal,
                self.bundle(),
                trusted_operator_id=60000287482,
                baseline_path=baseline,
            )
            with self.assertRaisesRegex(NativeApprovalError, "outside"):
                detect_native_approval(
                    self.proposal,
                    self.bundle(status=3),
                    trusted_operator_id=60000287482,
                    baseline_path=baseline,
                )

    def test_assignment_change_outside_note_workflow_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.json"
            detect_native_approval(
                self.proposal,
                self.bundle(),
                trusted_operator_id=60000287482,
                baseline_path=baseline,
            )
            with self.assertRaisesRegex(NativeApprovalError, "outside"):
                detect_native_approval(
                    self.proposal,
                    self.bundle(responder_id=7),
                    trusted_operator_id=60000287482,
                    baseline_path=baseline,
                )


if __name__ == "__main__":
    unittest.main()
