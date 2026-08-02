# Demo architecture and trust boundaries

```mermaid
flowchart LR
    FS[Freshservice\nsynthetic ticket #2]
    RG[Read-only gateway\nscoped ticket endpoint]
    C[Clem-managed Cora\nCodex runtime]
    KB[Curated Markdown KB]
    P[Validated proposal.json\nverbatim citations]
    AB[Isolated Civo AgentBus\nloopback only]
    UI[Live cockpit\ngaidemo-human identity]
    H{Human operator\nexact APPROVE?}
    W[Approval gateway\ngaidemo-operator identity]

    FS -->|official REST API| RG
    RG -->|ticket #2 only\nUnix socket; no API key| C
    KB -->|local search| C
    C --> P
    C -->|intake, research, proposal| AB
    AB --> UI
    P --> UI
    UI --> H
    H -->|reject / omit| X[No Freshservice write]
    H -->|hash-bound APPROVE| AB
    AB --> W
    W -->|proposal hash + stale-ticket guard\nthen private note + tags| FS
```

The Freshservice key is stored in `/etc/gaidemo/freshworks.env`, readable by
the approval-gateway identity but not Cora or the cockpit identity. Cora can
only use the ticket-scoped read gateway. The cockpit and approval gateway also
hold separate AgentBus mailbox tokens and cannot read each other's token.

This is a live capability demonstration over a synthetic scenario, not a production-readiness,
reliability, KPI, or vendor-selection result. Clem was selected because the
consultant already knows it well; alternatives should be evaluated separately
against the demonstrated control and capability bar.
