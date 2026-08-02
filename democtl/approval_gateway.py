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


HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def send_result(
    client: AgentBusClient,
    *,
    ticket_id: int,
    proposal_hash: str,
    approval_message_id: str,
    result: dict[str, Any],
) -> None:
    body = (
        f"Applied approved proposal {proposal_hash[:12]} to Freshservice ticket "
        f"#{ticket_id}: one private note plus ai-assisted and human-approved tags."
    )
    data = {
        "kind": "apply_result",
        "ticket_id": ticket_id,
        "proposal_hash": proposal_hash,
        "applied": True,
        "note_id": result.get("note_id"),
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


def process_message(
    client: AgentBusClient,
    message: dict[str, Any],
    *,
    ticket_id: int,
    proposal_path: Path,
    state_dir: Path,
) -> bool:
    data = message.get("data")
    if message.get("from") != "human-approval-bridge" or not isinstance(data, dict):
        return True
    proposal_hash = data.get("proposal_hash")
    if (
        data.get("kind") != "human_approval"
        or data.get("phrase") != "APPROVE"
        or data.get("ticket_id") != ticket_id
        or not isinstance(proposal_hash, str)
        or not HASH_RE.fullmatch(proposal_hash)
    ):
        return True
    expected_body = f"APPROVE ticket={ticket_id} proposal={proposal_hash}"
    if message.get("body") != expected_body:
        return True
    raw = proposal_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != proposal_hash:
        return True
    proposal = json.loads(raw)
    if not isinstance(proposal, dict) or proposal.get("ticket_id") != ticket_id:
        return True
    marker = state_dir / f"{ticket_id}-{proposal_hash}.json"
    if marker.exists():
        result = json.loads(marker.read_text(encoding="utf-8"))
    else:
        completed = subprocess.run(
            ["/usr/local/bin/gaidemo-proposal-apply", "APPROVE"],
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )
        if completed.returncode != 0:
            return False
        result = json.loads(completed.stdout)
        temporary = marker.with_suffix(".tmp")
        temporary.write_text(json.dumps(result), encoding="utf-8")
        os.replace(temporary, marker)
    send_result(
        client,
        ticket_id=ticket_id,
        proposal_hash=proposal_hash,
        approval_message_id=str(message["message_id"]),
        result=result,
    )
    return True


def main() -> None:
    ticket_id = int(os.environ["DEMO_TICKET_ID"])
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
