# Recording runbook

The final demo is assembled from three sanitized clips:

1. `freshworks-before.mp4`: synthetic ticket #1 before approval;
2. `terminal.mp4`: live Civo/Clem proposal preview, rejected write, and one
   explicit approved write;
3. `freshworks-after.mp4`: refreshed ticket showing the private note and tags.

Before recording, create the ignored `tmp/ssh/demo_config` with the Civo host,
the `civo` user, the disposable SSH key, and the existing ignored known-hosts
file. Keep the alias name `gaidemo`; the VHS PATH intentionally resolves
`ssh gaidemo` through `recording/bin/ssh` so no host, IP address, or username is
shown in the video.

Validate the tape without executing it:

```bash
vhs validate recording/terminal.tape
```

Run `vhs recording/terminal.tape` exactly once. Its final command performs the
approved Freshservice mutation and the ticket's stale-update guard prevents a
safe rehearsal from being reused after the live write.

The dedicated Chrome profile exposes DevTools only on loopback port 9222. Once
the operator has logged in and ticket #1 is visible, capture the content
viewport—never the browser chrome or desktop—with:

```bash
node recording/chrome-cdp.mjs status
node recording/chrome-cdp.mjs screenshot artifacts/freshworks-before.png
recording/still-to-clip.sh artifacts/freshworks-before.png \
  artifacts/freshworks-before.mp4 15
```

After the single approved write, reload ticket #1 and repeat with `after` in
the filenames. The capture command refuses any page whose path is not ticket
#1. This hides the address bar, tenant URL, account menus, extensions, desktop
notifications, and unrelated tickets by construction. Then assemble:

```bash
recording/assemble.sh
```

## AI-led cockpit replay

The v2 cut reframes the same verified run around the AI driving the work. A
conversation-first cockpit reports intake, scoped reading, knowledge evidence,
proposal creation, the no-write approval gate, the human approval, and the
operator-owned write. It switches to the native Freshservice before/after
captures and ends with a real ephemeral AgentBus conversation rendered through
AgentBus's capability-scoped operator UI.

The cockpit is explicitly a replay/prototype. It does not imply that the custom
conversation skin was connected during the original Freshservice mutation.

Generate the AgentBus evidence and record the complete v2 cut with one command:

```bash
recording/record-cockpit.sh
```

Outputs:

- `artifacts/ai-driven-freshservice-demo.mp4`
- `artifacts/agentbus-conversation.png`
- `artifacts/agentbus-conversation-late.png`

The AgentBus evidence process builds temporary binaries from the adjacent
AgentBus source tree, uses an isolated temporary SQLite database and token set,
binds only to loopback, and removes its runtime credentials on exit. Override
the source checkout with `AGENTBUS_REPO`; set `SKIP_AGENTBUS_EVIDENCE=1` only
when reusing an already-generated screenshot.
