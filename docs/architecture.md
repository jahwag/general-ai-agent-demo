# Demo architecture and trust boundaries

```mermaid
flowchart LR
    FS[Freshservice\nconfigured synthetic ticket]
    RG[Read-only gateway\nscoped ticket endpoint]
    C[Clem-managed Cora\nCodex runtime]
    KB[Curated Markdown KB]
    P[Validated proposal.json\nverbatim citations]
    AB[Isolated Civo AgentBus\nloopback only]
    G[Policy gateway\ngaidemo-operator identity]
    UI[AgentBus observability cockpit\ngaidemo-human identity]
    A[Native approval watcher\ngaidemo-approver identity]
    H[Human operator\nFreshservice workspace]

    FS -->|official REST API| RG
    RG -->|ticket only; Unix socket; no API key| C
    KB -->|local search| C
    C --> P
    C -->|intake and research| AB
    C -->|note_publish_request| AB
    P --> G
    AB --> G
    G -->|full hash + analyzed-version guard\nprivate note only; no approval| FS
    G -->|post-note metadata proposal| AB
    AB --> UI
    UI -->|read-only proposal projection| A
    H -->|optional exact approval note\nAPPROVE AI hash-prefix| FS
    RG -->|ticket + conversations; no API key| A
    A -->|authenticated metadata approval| AB
    AB --> G
    G -->|post-approval version guard\ntags only| FS
```

The Freshservice key is stored in `/etc/gaidemo/freshworks.env`, readable by the
`gaidemo-operator` gateway identity but not by Cora, the cockpit, or the native
approval watcher. Cora and the watcher can only use the ticket-scoped read
gateway. The cockpit, watcher, and policy gateway have distinct OS identities,
state directories, and AgentBus mailbox tokens. The cockpit endpoint returns
HTTP 410 for approval attempts: it is an observability surface, not a frontline
operator interface and not AgentBus itself.

The worker and gateway share only the validated proposal artifact through the
`gaidemo-proposals` group. The gateway accepts Cora's `note_publish_request`
only when the full artifact SHA-256, ticket ID, and analyzed ticket version all
match. It may then perform exactly one Freshservice action: add the grounded
private note. The note embeds the proposal hash as an idempotency and audit
reference. A persisted marker prevents Freshservice's eventually consistent
parent-ticket version from causing duplicate notes.

After the parent version settles, the gateway emits a metadata-only proposal.
The watcher accepts exactly one new private outgoing note whose text matches the
current proposal hash prefix and whose Freshservice `user_id` matches the
configured operator. It rejects concurrent ticket-field changes and additional
conversations. The gateway rechecks the full proposal SHA-256 and the ticket
version produced by that approval note, then applies tags only. A permanently
stale action emits an auditable rejection and is acknowledged instead of
poisoning the AgentBus delivery queue.

This is a live capability demonstration over a synthetic scenario, not a
production-readiness, reliability, KPI, legal-compliance, or vendor-selection
result. Clem was selected because the consultant already knows it well;
alternatives should be evaluated separately against the demonstrated control
capabilities.
