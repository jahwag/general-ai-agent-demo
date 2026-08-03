# General AI agent capability demo

Minimal, synthetic Freshservice capability demo for an internal product-owner
audience. The implemented path deliberately demonstrates risk-tiered autonomy:

1. a Clem-managed Codex worker reads one scoped Freshservice ticket;
2. it searches a curated Markdown knowledge base;
3. it publishes live intake and research events to an isolated AgentBus and
   writes a hash-bound structured proposal;
4. the policy gateway validates the artifact and ticket version, then publishes
   one grounded **private** note automatically;
5. the cockpit shows that real AgentBus trace but cannot approve anything;
6. a human may approve only the remaining ticket-metadata changes by adding the
   exact approval note inside Freshservice;
7. a separately identified watcher authenticates the note and the same gateway
   applies only the approved tags.

The private note is internal assistance, not a requester-visible reply. Public
replies and consequential ticket fields remain outside Cora's autonomous
permission. This is a capability demonstration, not production-readiness,
reliability, KPI, or EU AI Act conformity validation.

See `docs/demo-script.md` for the claims the recording may make and
`docs/architecture.md` for component trust boundaries.

## Local commands

```bash
python3 -m unittest discover -s tests
python3 -m democtl kb search "new phone wifi mfa"
python3 -m democtl ticket auth-check
python3 -m democtl ticket seed fixtures/tickets/replacement-phone.json
python3 -m democtl ticket seed fixtures/tickets/replacement-phone.json \
  --confirm "CREATE SYNTHETIC TICKET"
python3 -m democtl ticket show 123
python3 -m democtl proposal validate artifacts/proposal.json
python3 -m democtl proposal preview artifacts/proposal.json
python3 -m democtl proposal publish-note artifacts/proposal.json
python3 -m democtl proposal apply artifacts/proposal.json --approve APPROVE
```

The last two commands are administrator diagnostics. In the live demo Cora has
no Freshservice credential: it sends a `note_publish_request` to the policy
gateway. The gateway publishes the validated private note, then waits for an
operator to add `APPROVE AI <proposal-hash-prefix>` in Freshservice before it
applies metadata tags.

Freshservice credentials are read from the environment. Copy the ignored
`.env.example` to `.env`, set the tenant URL and demo-agent API key, and use only
synthetic data.
