# Demo script

Target length: 3–5 minutes. Audience: internal product owners familiar with
Codex/Claude Code but not responsible for implementation details.

## Claim

This is a live capability demonstration using synthetic data. Clem was chosen
because the consultant already knows it. The ticket read, Codex work, AgentBus
events, human approval, gateway write, and native Freshservice result are real;
the demo does not establish production readiness, reliability, KPI impact, or
a vendor recommendation.

## Storyboard

1. **Freshworks:** open the synthetic replacement-phone ticket and establish
   the operator problem.
2. **Live cockpit:** show Cora's AgentBus intake, grounded research, citations,
   and hash-bound proposal.
3. **Control:** point out that the human approval and operator gateway remain
   pending and that Freshservice is still unchanged.
4. **Approval:** let the human operator click once, confirm the exact ticket and
   proposal hash, and watch the separate gateway report the applied result.
5. **Freshworks:** refresh the ticket and show the approved note, citations,
   proposed category, and tags.
6. **Architecture card:** explain that production would replace the Markdown
   corpus with governed RAG, move model access behind customer-controlled
   inference, and evaluate Clem against managed alternatives such as AgentCore.

## Recording safety

- Record only the synthetic tenant/ticket and a cropped terminal.
- Hide URLs, IPs, account menus, browser extensions, notifications, and shell
  prompts containing host/user names.
- Never display `.env`, process environments, auth files, API headers, cloud
  dashboards, or command history containing credentials.
- Show elapsed progress honestly; do not imply an operator latency target.

## AI-led narration

Use the live cockpit and native Freshservice tabs as the visual spine:

1. **AI takes the initiative.** Cora receives the scoped ticket event, states
   what it will do, and makes its lack of Freshservice write access explicit.
2. **AI reports work as a conversation.** It summarizes the diagnosis, cites
   three governed knowledge articles, and emits an immutable proposal hash.
3. **Freshservice remains unchanged.** Switch to the native ticket before
   approval; no private note or audit tags exist yet.
4. **Human control is narrow and consequential.** The approval gateway refuses
   to mutate until a human provides the exact approval for that ticket and
   proposal. The gateway—not the model—holds the write credential.
5. **Native proof.** Switch back to Freshservice after approval and show the
   private note plus `ai-assisted` and `human-approved` tags.
6. **Technical proof.** End on the real AgentBus operator conversation: Cora,
   the approval gateway, and the human approval bridge emitted a durable reply
   chain. Explain that Discord could be another presentation surface, while
    AgentBus supplies delivery, retention, and audit semantics beneath it.

Do not present the older cockpit prototype or AgentBus replay as the live run.
The recorded demo must use the isolated Civo AgentBus and its live cockpit.
