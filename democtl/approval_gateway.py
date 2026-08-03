from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from .agentbus_client import AgentBusClient, AgentBusConfig, AgentBusError
from .proposal import STALE_TICKET_ERROR


HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _proposal_for_message(
    proposal_path: Path,
    *,
    proposal_hash: str,
    ticket_id: int,
) -> dict[str, Any] | None:
    raw = proposal_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != proposal_hash:
        return None
    proposal = json.loads(raw)
    if not isinstance(proposal, dict) or proposal.get("ticket_id") != ticket_id:
        return None
    return proposal


def _run_action(action: str, expected_updated_at: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "/usr/local/bin/gaidemo-proposal-apply",
            action,
            expected_updated_at,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )


def _permanent_rejection_reason(
    completed: subprocess.CompletedProcess[str],
) -> str | None:
    try:
        value = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(value, dict) and value.get("error") == STALE_TICKET_ERROR:
        return "ticket_version_changed"
    return None


def _ticket_updated_at(ticket_id: int) -> str:
    completed = subprocess.run(
        ["/usr/local/bin/gaidemo-ticket-read", str(ticket_id)],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    bundle = json.loads(completed.stdout)
    ticket = bundle.get("ticket") if isinstance(bundle, dict) else None
    updated_at = ticket.get("updated_at") if isinstance(ticket, dict) else None
    if not isinstance(updated_at, str) or not updated_at:
        raise ValueError("ticket reader returned no updated_at")
    return updated_at


def _send_note_ready(
    client: AgentBusClient,
    *,
    ticket_id: int,
    proposal_hash: str,
    request_message_id: str,
    proposal: dict[str, Any],
    result: dict[str, Any],
    ticket_updated_at: str,
) -> None:
    tags = proposal.get("tags_to_add")
    if not isinstance(tags, list):
        tags = []
    evidence = proposal.get("evidence")
    citations = (
        [
            item["citation"]
            for item in evidence
            if isinstance(item, dict) and isinstance(item.get("citation"), str)
        ]
        if isinstance(evidence, list)
        else []
    )
    client.send(
        to="human-approval-bridge",
        body=(
            f"Cora published private guidance on Freshservice ticket #{ticket_id} "
            "without a human approval step. The private note is now available to "
            f"the operator; approval is requested only for metadata tags: {tags}."
        ),
        client_message_id=(
            f"ticket-{ticket_id}-note-published-{proposal_hash[:12]}"
        ),
        data={
            "kind": "proposal_ready",
            "ticket_id": ticket_id,
            "proposal_hash": proposal_hash,
            "ticket_updated_at": ticket_updated_at,
            "category": proposal.get("category"),
            "citations": citations,
            "tags_to_add": tags,
            "note_id": result.get("note_id"),
            "private_note_published": True,
            "approval_scope": ["tags"],
        },
        reply_to=request_message_id,
    )


def _send_note_rejection(
    client: AgentBusClient,
    *,
    ticket_id: int,
    proposal_hash: str,
    request_message_id: str,
) -> None:
    client.send(
        to="human-approval-bridge",
        body=(
            f"Safety guard refused Cora's private note {proposal_hash[:12]} for "
            f"Freshservice ticket #{ticket_id} because the ticket version changed. "
            "No note was published."
        ),
        client_message_id=(
            f"ticket-{ticket_id}-note-rejected-{proposal_hash[:12]}-"
            f"{request_message_id[-12:]}"
        ),
        data={
            "kind": "note_rejected",
            "ticket_id": ticket_id,
            "proposal_hash": proposal_hash,
            "reason": "ticket_version_changed",
        },
        reply_to=request_message_id,
    )


def _send_apply_result(
    client: AgentBusClient,
    *,
    ticket_id: int,
    proposal_hash: str,
    approval_message_id: str,
    result: dict[str, Any],
) -> None:
    body = (
        f"Applied the human-approved metadata changes from proposal "
        f"{proposal_hash[:12]} to Freshservice ticket #{ticket_id}. "
        "Cora's private guidance had already been published autonomously."
    )
    data = {
        "kind": "apply_result",
        "ticket_id": ticket_id,
        "proposal_hash": proposal_hash,
        "applied": True,
        "approved_changes": result.get("approved_changes", ["tags"]),
        "tags": result.get("tags"),
    }
    for recipient, suffix in (
        ("human-approval-bridge", "operator"),
        ("cora", "cora"),
    ):
        client.send(
            to=recipient,
            body=body,
            client_message_id=(
                f"ticket-{ticket_id}-apply-result-{proposal_hash[:12]}-{suffix}"
            ),
            data=data,
            reply_to=approval_message_id,
        )


def _send_apply_rejection(
    client: AgentBusClient,
    *,
    ticket_id: int,
    proposal_hash: str,
    approval_message_id: str,
) -> None:
    client.send(
        to="cora",
        body=(
            f"Safety guard refused the metadata changes from proposal "
            f"{proposal_hash[:12]} for Freshservice ticket #{ticket_id} because "
            "the ticket version changed. The existing private guidance remains, "
            "but no approval-gated field write was applied."
        ),
        client_message_id=(
            f"ticket-{ticket_id}-apply-rejected-{proposal_hash[:12]}-"
            f"{approval_message_id[-12:]}"
        ),
        data={
            "kind": "apply_rejected",
            "ticket_id": ticket_id,
            "proposal_hash": proposal_hash,
            "reason": "ticket_version_changed",
        },
        reply_to=approval_message_id,
    )


def _process_note_request(
    client: AgentBusClient,
    message: dict[str, Any],
    data: dict[str, Any],
    *,
    ticket_id: int,
    proposal_path: Path,
    state_dir: Path,
) -> bool:
    proposal_hash = data.get("proposal_hash")
    expected_updated_at = data.get("ticket_updated_at")
    request_message_id = message.get("message_id")
    if (
        data.get("ticket_id") != ticket_id
        or not isinstance(proposal_hash, str)
        or not HASH_RE.fullmatch(proposal_hash)
        or not isinstance(expected_updated_at, str)
        or not isinstance(request_message_id, str)
    ):
        return True
    proposal = _proposal_for_message(
        proposal_path, proposal_hash=proposal_hash, ticket_id=ticket_id
    )
    if proposal is None or proposal.get("ticket_updated_at") != expected_updated_at:
        return True

    marker = state_dir / f"note-{ticket_id}-{proposal_hash}.json"
    if marker.exists():
        result = json.loads(marker.read_text(encoding="utf-8"))
    else:
        completed = _run_action("NOTE", expected_updated_at)
        if completed.returncode != 0:
            reason = _permanent_rejection_reason(completed)
            if reason is None:
                return False
            _send_note_rejection(
                client,
                ticket_id=ticket_id,
                proposal_hash=proposal_hash,
                request_message_id=request_message_id,
            )
            return True
        result = json.loads(completed.stdout)
        if not isinstance(result, dict) or result.get("published") is not True:
            return False
        _write_json(marker, result)

    ticket_updated_at = _ticket_updated_at(ticket_id)
    if ticket_updated_at == result.get("ticket_updated_at_before"):
        # Freshservice can expose the note before the parent ticket version settles.
        # The persisted note marker prevents a retry from publishing it twice.
        return False
    _send_note_ready(
        client,
        ticket_id=ticket_id,
        proposal_hash=proposal_hash,
        request_message_id=request_message_id,
        proposal=proposal,
        result=result,
        ticket_updated_at=ticket_updated_at,
    )
    return True


def _process_human_approval(
    client: AgentBusClient,
    message: dict[str, Any],
    data: dict[str, Any],
    *,
    ticket_id: int,
    trusted_operator_id: int,
    proposal_path: Path,
    state_dir: Path,
) -> bool:
    proposal_hash = data.get("proposal_hash")
    expected_updated_at = data.get("ticket_updated_at")
    approval_message_id = message.get("message_id")
    if (
        data.get("phrase") != "APPROVE"
        or data.get("source") != "freshservice_private_note"
        or data.get("ticket_id") != ticket_id
        or data.get("operator_user_id") != trusted_operator_id
        or not isinstance(data.get("approval_conversation_id"), int)
        or not isinstance(expected_updated_at, str)
        or not isinstance(proposal_hash, str)
        or not HASH_RE.fullmatch(proposal_hash)
        or not isinstance(approval_message_id, str)
    ):
        return True
    expected_body = f"APPROVE ticket={ticket_id} proposal={proposal_hash}"
    if message.get("body") != expected_body:
        return True
    proposal = _proposal_for_message(
        proposal_path, proposal_hash=proposal_hash, ticket_id=ticket_id
    )
    if proposal is None:
        return True

    marker = state_dir / f"{ticket_id}-{proposal_hash}.json"
    if marker.exists():
        result = json.loads(marker.read_text(encoding="utf-8"))
    else:
        completed = _run_action("APPROVE", expected_updated_at)
        if completed.returncode != 0:
            reason = _permanent_rejection_reason(completed)
            if reason is None:
                return False
            _send_apply_rejection(
                client,
                ticket_id=ticket_id,
                proposal_hash=proposal_hash,
                approval_message_id=approval_message_id,
            )
            return True
        result = json.loads(completed.stdout)
        if not isinstance(result, dict) or result.get("applied") is not True:
            return False
        _write_json(marker, result)

    _send_apply_result(
        client,
        ticket_id=ticket_id,
        proposal_hash=proposal_hash,
        approval_message_id=approval_message_id,
        result=result,
    )
    return True


def process_message(
    client: AgentBusClient,
    message: dict[str, Any],
    *,
    ticket_id: int,
    trusted_operator_id: int,
    proposal_path: Path,
    state_dir: Path,
) -> bool:
    data = message.get("data")
    if not isinstance(data, dict):
        return True
    if (
        message.get("from") == "cora"
        and data.get("kind") == "note_publish_request"
    ):
        return _process_note_request(
            client,
            message,
            data,
            ticket_id=ticket_id,
            proposal_path=proposal_path,
            state_dir=state_dir,
        )
    if (
        message.get("from") == "freshservice-approval-bridge"
        and data.get("kind") == "human_approval"
    ):
        return _process_human_approval(
            client,
            message,
            data,
            ticket_id=ticket_id,
            trusted_operator_id=trusted_operator_id,
            proposal_path=proposal_path,
            state_dir=state_dir,
        )
    return True


def main() -> None:
    ticket_id = int(os.environ["DEMO_TICKET_ID"])
    trusted_operator_id = int(os.environ["DEMO_OPERATOR_ID"])
    proposal_path = Path(os.environ["GAIDEMO_PROPOSAL_PATH"])
    state_dir = Path(os.environ["GAIDEMO_APPROVAL_STATE_DIR"])
    state_dir.mkdir(parents=True, exist_ok=True)
    client = AgentBusClient(
        AgentBusConfig(
            server=os.environ["AGENTBUS_SERVER"],
            token_file=Path(os.environ["AGENTBUS_GATEWAY_TOKEN_FILE"]),
        )
    )
    while True:
        try:
            delivery = client.wait(timeout=20)
            if delivery is None:
                continue
            accepted = True
            for message in delivery["messages"]:
                if isinstance(message, dict):
                    accepted = process_message(
                        client,
                        message,
                        ticket_id=ticket_id,
                        trusted_operator_id=trusted_operator_id,
                        proposal_path=proposal_path,
                        state_dir=state_dir,
                    ) and accepted
            if accepted:
                client.ack(delivery["delivery_id"])
            else:
                time.sleep(3)
        except (AgentBusError, OSError, ValueError, subprocess.SubprocessError):
            time.sleep(3)


if __name__ == "__main__":
    main()
