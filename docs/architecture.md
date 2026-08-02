# Demo architecture and trust boundaries

```mermaid
flowchart LR
    FS[Freshservice\nsynthetic ticket #1]
    GW[Read-only gateway\noperator OS identity]
    C[Clem-managed Cora\nCodex runtime]
    KB[Curated Markdown KB]
    P[Validated proposal.json\nverbatim citations]
    H{Human operator\nexact APPROVE?}
    W[Deterministic write executor\nprivate note + tags]

    FS -->|official REST API| GW
    GW -->|ticket #1 only\nUnix socket; no API key| C
    KB -->|local search| C
    C --> P
    P --> H
    H -->|reject / omit| X[No Freshservice write]
    H -->|APPROVE| W
    W -->|stale-ticket guard\nthen approved mutation| FS
```

The Freshservice key is stored in `/etc/gaidemo/freshworks.env`, readable by
the operator identity but not the Clem agent. The gateway has no mutation
route and rejects every ticket ID except the configured synthetic ticket.

This is a scripted capability demonstration, not a production-readiness,
reliability, KPI, or vendor-selection result. Clem was selected because the
consultant already knows it well; alternatives should be evaluated separately
against the demonstrated control and capability bar.
