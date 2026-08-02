from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .freshworks import FreshworksClient, FreshworksConfig
from .knowledge import KnowledgeBase
from .proposal import ProposalError, apply_proposal, load_and_validate_proposal
from .ticket_fixture import load_synthetic_ticket


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="democtl")
    parser.add_argument(
        "--kb-dir",
        type=Path,
        default=Path("fixtures/kb"),
        help="directory containing Markdown knowledge articles",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    kb = commands.add_parser("kb")
    kb_commands = kb.add_subparsers(dest="kb_command", required=True)
    kb_search = kb_commands.add_parser("search")
    kb_search.add_argument("query")
    kb_search.add_argument("--limit", type=int, default=3)

    ticket = commands.add_parser("ticket")
    ticket_commands = ticket.add_subparsers(dest="ticket_command", required=True)
    ticket_show = ticket_commands.add_parser("show")
    ticket_show.add_argument("ticket_id", type=int)
    ticket_commands.add_parser("auth-check")
    ticket_seed = ticket_commands.add_parser("seed")
    ticket_seed.add_argument("path", type=Path)
    ticket_seed.add_argument(
        "--confirm",
        metavar="PHRASE",
        help='must exactly "CREATE SYNTHETIC TICKET"; omission is a dry run',
    )

    proposal = commands.add_parser("proposal")
    proposal_commands = proposal.add_subparsers(
        dest="proposal_command", required=True
    )
    for name in ("validate", "preview"):
        command = proposal_commands.add_parser(name)
        command.add_argument("path", type=Path)
    proposal_apply = proposal_commands.add_parser("apply")
    proposal_apply.add_argument("path", type=Path)
    proposal_apply.add_argument(
        "--approve",
        metavar="PHRASE",
        help='must be exactly "APPROVE"; omission is always a dry run',
    )
    return parser


def print_json(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    knowledge = KnowledgeBase(args.kb_dir)

    try:
        if args.command == "kb":
            print_json(knowledge.search(args.query, limit=args.limit))
            return 0

        if args.command == "ticket" and args.ticket_command == "show":
            client = FreshworksClient(FreshworksConfig.from_environment())
            print_json(client.get_ticket_bundle(args.ticket_id))
            return 0

        if args.command == "ticket" and args.ticket_command == "auth-check":
            client = FreshworksClient(FreshworksConfig.from_environment())
            print_json(client.check_authentication())
            return 0

        if args.command == "ticket" and args.ticket_command == "seed":
            ticket = load_synthetic_ticket(args.path)
            if args.confirm != "CREATE SYNTHETIC TICKET":
                print_json(
                    {
                        "action": "not_applied",
                        "reason": (
                            "explicit operator phrase --confirm "
                            '"CREATE SYNTHETIC TICKET" required'
                        ),
                        "ticket": ticket,
                    }
                )
                return 3
            client = FreshworksClient(FreshworksConfig.from_environment())
            created = client.create_ticket(ticket)
            print_json(
                {
                    "action": "created",
                    "ticket_id": created.get("id"),
                    "subject": created.get("subject", ticket["subject"]),
                    "tags": created.get("tags", ticket["tags"]),
                }
            )
            return 0

        proposal = load_and_validate_proposal(args.path, knowledge)
        if args.proposal_command == "validate":
            print_json({"valid": True, "ticket_id": proposal["ticket_id"]})
            return 0
        if args.proposal_command == "preview":
            print_json({"mode": "preview", "proposal": proposal})
            return 0
        if args.approve != "APPROVE":
            print_json(
                {
                    "applied": False,
                    "reason": 'explicit operator phrase --approve "APPROVE" required',
                    "proposal": proposal,
                }
            )
            return 3
        client = FreshworksClient(FreshworksConfig.from_environment())
        print_json(apply_proposal(client, proposal))
        return 0
    except (OSError, ValueError, ProposalError) as exc:
        print_json({"error": str(exc)})
        return 2


if __name__ == "__main__":
    sys.exit(main())
