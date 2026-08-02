# Demo script

Target length: 3–5 minutes. Audience: internal product owners familiar with
Codex/Claude Code but not responsible for implementation details.

## Claim

This is a scripted capability demonstration using synthetic data. Clem was
chosen because the consultant already knows it. The demo does not establish
production readiness, reliability, KPI impact, or a vendor recommendation.

## Storyboard

1. **Freshworks:** open the synthetic replacement-phone ticket and establish
   the operator problem.
2. **Clem/Codex:** show the agent fetch the ticket, search the local knowledge
   corpus, and produce a structured proposal with verbatim evidence.
3. **Control:** preview the proposal; demonstrate that omission of the exact
   approval phrase produces no write.
4. **Approval:** enter the approval phrase as the operator and apply the private
   note plus tags.
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

## V2: AI-led narration

Use `artifacts/ai-driven-freshservice-demo.mp4` as the short visual spine and
pause it while narrating where useful:

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

Do not say the custom cockpit was live during the original run. Call it a
verified-run interaction prototype backed by native Freshservice evidence and a
real isolated AgentBus replay.
