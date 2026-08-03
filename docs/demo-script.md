# Demo script

Target length: 3–5 minutes. Audience: internal product owners familiar with
Codex or Claude Code but not responsible for implementation details.

## Claim

This is a live capability demonstration using synthetic data. Clem was chosen
because the consultant already knows it. The ticket read, Codex work, AgentBus
events, autonomous private note, human metadata approval, guarded write, and
Freshservice result are real.

## Sequence

1. **Freshservice:** show a configured synthetic ticket with no AI guidance.
2. **Cora:** show the read-only Clem-managed session claiming the synthetic
   task, reading the scoped ticket, searching the curated KB, and validating a
   hash-bound proposal.
3. **AgentBus:** show intake, grounded research, citations, and Cora requesting
   publication of one private note. Explain that the custom cockpit is an
   observability view, not AgentBus and not an approval interface.
4. **Autonomous low-risk action:** refresh Freshservice and show Cora's private
   guidance, evidence, and recommendation already present. No human approval
   was required because it is internal, auditable, and does not change ticket
   fields or message the requester.
5. **Narrow boundary:** show that the metadata tags are still pending. If the
   demo includes approval, let the human add the exact private note shown by the
   proposal: `APPROVE AI <12-character hash prefix>`.
6. **Native proof:** show the watcher authenticating the Freshservice identity
   and exact proposal, then refresh to show only the approved tags applied.
7. **Technical proof:** show Cora, policy gateway, native approval watcher, and
   guarded write in one real AgentBus reply chain.
8. **Architecture card:** explain that production would replace the Markdown
   corpus with governed retrieval, place inference behind customer controls,
   and evaluate Clem against managed alternatives such as AgentCore.

## Message to land

- Human oversight is risk-tiered, not a blanket approval dialog.
- The operator gets useful assistance in the Freshservice workspace they
  already use.
- Cora never receives the Freshservice credential.
- Public replies and ticket-field changes are outside autonomous scope.
- AgentBus supplies authenticated senders, delivery, idempotency, and an audit
  chain beneath the presentation surface.

## Recording safety

- Record only the synthetic tenant and ticket; crop terminals.
- Hide URLs, IPs, account menus, browser extensions, notifications, and shell
  prompts containing host or user names.
- Never display `.env`, process environments, auth files, API keys, mailbox
  tokens, SSH keys, or browser cookies.
- Do not automate the human's optional Freshservice metadata-approval note.
- Do not present the older cockpit-click prototype or replayed events as a live
  run.
