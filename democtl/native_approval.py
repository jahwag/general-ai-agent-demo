from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .agentbus_client import AgentBusClient, AgentBusConfig, AgentBusError


TICKET_FINGERPRINT_FIELDS = (
    "id",
    "requester_id",
    "responder_id",
    "group_id",
    "subject",
    "description_text",
    "status",
    "priority",
    "impact",
    "urgency",
    "source",
    "type",
    "category",
    "sub_category",
    "item_category",
    "tags",
    "created_at",
)


class NativeApprovalError(ValueError):
    pass


def approval_command(proposal_hash: str) -> str:
    if len(proposal_hash) != 64 or any(c not in "0123456789abcdef" for c in proposal_hash):
        raise NativeApprovalError("proposal hash was invalid")
    return f"APPROVE AI {proposal_hash[:12]}"


def _fingerprint(ticket: dict[str, Any]) -> str:
    selected = {key: ticket.get(key) for key in TICKET_FINGERPRINT_FIELDS}
    raw = json.dumps(selected, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def detect_native_approval(
    proposal: dict[str, Any],
    bundle: dict[str, Any],
    *,
    trusted_operator_id: int,
    baseline_path: Path,
) -> dict[str, Any] | None:
    ticket_id = proposal.get("ticket_id")
    proposal_hash = proposal.get("proposal_hash")
    ticket_updated_at = proposal.get("ticket_updated_at")
    proposal_message_id = proposal.get("message_id")
    if (
        not isinstance(ticket_id, int)
        or not isinstance(proposal_hash, str)
        or not isinstance(ticket_updated_at, str)
        or not isinstance(proposal_message_id, str)
    ):
        raise NativeApprovalError("proposal descriptor was incomplete")
    ticket = bundle.get("ticket")
    conversations = bundle.get("conversations")
    if not isinstance(ticket, dict) or not isinstance(conversations, list):
        raise NativeApprovalError("ticket bundle was invalid")
    if ticket.get("id") != ticket_id:
        raise NativeApprovalError("ticket bundle did not match the proposal")
    if any(not isinstance(item, dict) for item in conversations):
        raise NativeApprovalError("ticket conversations were invalid")

    if not baseline_path.exists():
        if ticket.get("updated_at") != ticket_updated_at:
            raise NativeApprovalError("ticket changed before native approval monitoring")
        conversation_ids = [item.get("id") for item in conversations]
        if any(not isinstance(value, int) for value in conversation_ids):
            raise NativeApprovalError("conversation ID was invalid")
        _write_json(
            baseline_path,
            {
                "ticket_id": ticket_id,
                "proposal_hash": proposal_hash,
                "ticket_fingerprint": _fingerprint(ticket),
                "conversation_ids": conversation_ids,
            },
        )
        return None

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if (
        baseline.get("ticket_id") != ticket_id
        or baseline.get("proposal_hash") != proposal_hash
        or baseline.get("ticket_fingerprint") != _fingerprint(ticket)
    ):
        raise NativeApprovalError("ticket changed outside the approval-note workflow")
    known_ids = baseline.get("conversation_ids")
    if not isinstance(known_ids, list) or any(not isinstance(value, int) for value in known_ids):
        raise NativeApprovalError("native approval baseline was invalid")
    new_conversations = [item for item in conversations if item.get("id") not in known_ids]
    if not new_conversations:
        return None
    if len(new_conversations) != 1:
        raise NativeApprovalError("more than one conversation appeared after proposal review")
    approval = new_conversations[0]
    if (
        approval.get("private") is not True
        or approval.get("incoming") is not False
        or approval.get("user_id") != trusted_operator_id
        or str(approval.get("body_text") or "").strip() != approval_command(proposal_hash)
        or not isinstance(approval.get("id"), int)
    ):
        raise NativeApprovalError("new conversation was not the exact trusted approval note")
    current_updated_at = ticket.get("updated_at")
    if not isinstance(current_updated_at, str):
        raise NativeApprovalError("ticket updated_at was invalid")
    return {
        "ticket_id": ticket_id,
        "proposal_hash": proposal_hash,
        "proposal_message_id": proposal_message_id,
        "approval_conversation_id": approval["id"],
        "operator_user_id": trusted_operator_id,
        "ticket_updated_at": current_updated_at,
    }


def _read_ticket(ticket_id: int) -> dict[str, Any]:
    completed = subprocess.run(
        ["/usr/local/bin/gaidemo-ticket-read", str(ticket_id)],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    value = json.loads(completed.stdout)
    if not isinstance(value, dict):
        raise NativeApprovalError("ticket reader returned a non-object")
    return value


def publish_native_approval(
    client: AgentBusClient,
    ticket_id: int,
    approval: dict[str, Any],
) -> dict[str, str]:
    proposal_hash = approval.get("proposal_hash")
    proposal_message_id = approval.get("proposal_message_id")
    if not isinstance(proposal_hash, str):
        raise NativeApprovalError("native approval lacked a proposal hash")
    approval_command(proposal_hash)
    if not isinstance(proposal_message_id, str):
        raise NativeApprovalError("native approval lacked a proposal message ID")

    audit = client.send(
        to="human-approval-bridge",
        body=(
            f"Human operator approved proposal {proposal_hash[:12]} "
            f"inside Freshservice ticket #{ticket_id}."
        ),
        client_message_id=(
            f"ticket-{ticket_id}-freshservice-approval-audit-"
            f"{proposal_hash[:12]}"
        ),
        data={
            "kind": "approval_verified",
            "source": "freshservice_private_note",
            **approval,
        },
        reply_to=proposal_message_id,
    )
    sent = client.send(
        to="approval-gateway",
        body=f"APPROVE ticket={ticket_id} proposal={proposal_hash}",
        client_message_id=(
            f"ticket-{ticket_id}-freshservice-approval-{proposal_hash[:12]}"
        ),
        data={
            "kind": "human_approval",
            "phrase": "APPROVE",
            "source": "freshservice_private_note",
            **approval,
        },
        reply_to=proposal_message_id,
    )
    return {
        "message_id": sent["message_id"],
        "audit_message_id": audit["message_id"],
    }


def main() -> None:
    ticket_id = int(os.environ["DEMO_TICKET_ID"])
    trusted_operator_id = int(os.environ["DEMO_OPERATOR_ID"])
    state_dir = Path(os.environ["GAIDEMO_NATIVE_APPROVAL_STATE_DIR"])
    proposal_path = Path(os.environ["GAIDEMO_PROPOSAL_DESCRIPTOR_PATH"])
    client = AgentBusClient(
        AgentBusConfig(
            server=os.environ["AGENTBUS_SERVER"],
            token_file=Path(os.environ["AGENTBUS_NATIVE_APPROVAL_TOKEN_FILE"]),
        )
    )
    while True:
        try:
            if not proposal_path.exists():
                time.sleep(2)
                continue
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            if not isinstance(proposal, dict) or proposal.get("ticket_id") != ticket_id:
                raise NativeApprovalError("current proposal did not match the demo ticket")
            proposal_hash = proposal.get("proposal_hash")
            if not isinstance(proposal_hash, str):
                raise NativeApprovalError("current proposal lacked a hash")
            marker = state_dir / f"native-approved-{ticket_id}-{proposal_hash}.json"
            if marker.exists():
                time.sleep(2)
                continue
            baseline = state_dir / f"native-baseline-{ticket_id}-{proposal_hash}.json"
            approval = detect_native_approval(
                proposal,
                _read_ticket(ticket_id),
                trusted_operator_id=trusted_operator_id,
                baseline_path=baseline,
            )
            if approval is None:
                time.sleep(2)
                continue
            published = publish_native_approval(client, ticket_id, approval)
            _write_json(
                marker,
                {
                    **approval,
                    **published,
                },
            )
        except (
            AgentBusError,
            NativeApprovalError,
            OSError,
            ValueError,
            subprocess.SubprocessError,
        ) as exc:
            print(
                f"native approval watcher: {type(exc).__name__}: {exc}",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(3)


if __name__ == "__main__":
    main()
