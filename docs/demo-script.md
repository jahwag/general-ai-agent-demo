# Demo script

Target length: 3–5 minutes. Audience: internal product owners who know what
Codex and Claude Code are but do not need implementation-level detail.

## Claim

This is a live capability demonstration using synthetic data. The BookStack
pages, Codex work, AgentBus events, citation validation, and Freshservice note
are real. Clem was chosen because the consultant knows it well; the demo sets a
control and usability bar rather than pre-deciding the customer platform.

## Sequence

1. **Knowledge entering the system.** Show the BookStack runbook containing
   three approved articles. Open one page and point out owner, status, review
   date, revision number, and the actual operating instruction. Say:
   “BookStack is the governed source here, not the RAG engine. Confluence can
   replace this connector.”
2. **Freshservice request.** Show the synthetic replacement-phone ticket with
   no AI guidance yet.
3. **Cora working.** Show the real Clem/Codex terminal reading the scoped
   ticket, issuing BookStack searches, reading exact pages, and constructing a
   proposal with verbatim `bookstack://...@revision-N` evidence.
4. **Auditable coordination.** Show the actual AgentBus UI with Cora's intake,
   research result, cited page titles/revisions, and private-note publication
   request. Do not show the custom cockpit in the main cut.
5. **Assistance where the operator works.** Refresh Freshservice and show
   Cora's private note, the linked BookStack titles and revisions, the quoted
   evidence, recommendation, and proposal hash. No separate approval screen was
   required for this low-risk internal note.
6. **Optional control boundary.** Explain or demonstrate that metadata tags
   remain pending until a human adds `APPROVE AI <hash-prefix>` as a private
   Freshservice note. Public replies and consequential field changes remain out
   of scope.

## Message to land

- Knowledge has an owner and lifecycle; retrieval is not a mysterious upload
  into a model.
- The agent cites exact, current source revisions and fails closed when a page
  changes.
- Human oversight is risk-tiered and occurs in Freshservice, the operator's
  existing workspace.
- Cora receives neither Freshservice nor BookStack credentials.
- AgentBus provides a real cross-agent audit trail; the UI shown is AgentBus's
  own UI.
- The next increment is an agent-proposed BookStack or Confluence draft that a
  knowledge owner reviews and publishes.

Never record `.env` files, API keys, mailbox tokens, SSH hosts, browser cookies,
account settings, notifications, or non-synthetic tickets. Do not automate the
human's optional metadata approval.
