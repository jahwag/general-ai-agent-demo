# General AI agent capability demo

Minimal, synthetic Freshworks capability demo for an internal product-owner
audience. The implemented path is deliberately small:

1. a Clem-managed Codex worker reads one Freshworks ticket;
2. it searches a curated Markdown knowledge base;
3. it publishes live intake, research, and proposal events to an isolated
   AgentBus and writes a hash-bound structured proposal;
4. the cockpit shows the live AgentBus run but cannot approve anything;
5. the human approves with an exact private note inside Freshservice;
6. a separately identified watcher authenticates that note and emits approval;
7. a deterministic write gateway adds one solution note and two demo tags.

The demo is not a production-readiness, reliability, or KPI validation. See
`docs/demo-script.md` for the intended recording and the claims it may make.
The component trust boundaries are documented in `docs/architecture.md`.

## Local commands

```bash
python -m unittest discover -s tests
python -m democtl kb search "new phone wifi mfa"
python -m democtl ticket auth-check
python -m democtl ticket seed fixtures/tickets/replacement-phone.json
python -m democtl ticket seed fixtures/tickets/replacement-phone.json \
  --confirm "CREATE SYNTHETIC TICKET"
python -m democtl ticket show 123
python -m democtl proposal validate artifacts/proposal.json
python -m democtl proposal preview artifacts/proposal.json
python -m democtl proposal apply artifacts/proposal.json --approve APPROVE
```

The last command is an administrator-level diagnostic path. In the live demo,
the operator never runs it: they add `APPROVE AI <proposal-hash-prefix>` as a
private Freshservice note, and the guarded gateway applies the hash-bound
proposal only after the native approval watcher validates the note.

Freshworks credentials are read from the environment. Copy `.env.example` to
the ignored `.env`, then set the tenant URL and demo-agent API key. Use only
synthetic data.
