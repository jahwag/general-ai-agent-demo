# Demo script

Target length: 3–5 minutes. Audience: internal product owners familiar with
Codex or Claude Code but not responsible for implementation details.

## Claim

This is a live capability demonstration using synthetic data. Clem was chosen
because the consultant already knows it. The ticket read, Codex work, AgentBus
events, human approval, guarded write, and native Freshservice result are real.
The demo does not establish production readiness, reliability, KPI impact, or
a vendor recommendation.

## Storyboard

1. **Freshservice:** open the synthetic replacement-phone ticket and establish
   the operator's problem.
2. **Cora console:** show the read-only web terminal attached to the real
   Clem-managed Codex session as Cora claims the synthetic GitHub task, reads
   the scoped ticket, searches the curated KB, and validates its proposal.
3. **AgentBus observability:** show Cora's live intake, grounded research,
   citations, and hash-bound proposal in the cockpit. Say explicitly that this
   custom view is not AgentBus and is not the operator's approval interface.
4. **Control:** point out that human approval and the write gateway remain
   pending and the ticket has no AI solution note or approval tags.
5. **Native approval:** in Freshservice, let the human add the exact private
   note shown for the proposal: `APPROVE AI <12-character hash prefix>`. The
   separate watcher verifies the authenticated agent, unchanged ticket, and
   exact note before emitting a real AgentBus approval event.
6. **Native proof:** refresh Freshservice and show the gateway-applied solution
   note, citations, category recommendation, and the `ai-assisted` and
   `human-approved` tags.
7. **Technical proof:** switch to the cockpit and show Cora, the native approval
   watcher, and the write gateway in one durable AgentBus reply chain.
8. **Architecture card:** explain that production would replace the Markdown
   corpus with governed retrieval, place model access behind a
   customer-controlled inference gateway, and evaluate Clem against managed
   alternatives such as AgentCore.

## Recording safety

- Record only the synthetic tenant and ticket, with a cropped terminal.
- Hide URLs, IPs, account menus, browser extensions, notifications, and shell
  prompts containing host or user names.
- Never display `.env`, process environments, auth files, API keys, mailbox
  tokens, SSH keys, or browser cookies.
- Do not automate the human's Freshservice approval note.
- Start from a fresh proposal run and show the ticket before and after approval.

## Presenter proof points

1. **The AI is scoped.** Cora reports the ticket intake, states what it will do,
   and makes its lack of Freshservice write access explicit.
2. **The AI reports its work.** It summarizes the diagnosis, cites governed
   knowledge articles, and emits an immutable proposal hash.
3. **Freshservice is unchanged before approval.** No solution note or approval
   tags exist yet.
4. **Human control is narrow and consequential.** Approval happens in the
   operator's existing Freshservice workspace, not the custom cockpit. The
   gateway refuses to mutate until the watcher authenticates the exact private
   note for that ticket and proposal. The gateway—not the model or cockpit—holds
   the write credential.
5. **The result is native.** The approved solution and audit tags appear on the
   Freshservice ticket.
6. **The orchestration is real.** AgentBus supplies authenticated senders,
   delivery, idempotency, and the reply chain beneath the presentation surface.

Do not present the older cockpit-click prototype or an AgentBus event replay as
the live run. The recorded demo must use the isolated Civo AgentBus and native
Freshservice approval flow.
