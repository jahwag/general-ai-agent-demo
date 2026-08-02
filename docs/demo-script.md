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
