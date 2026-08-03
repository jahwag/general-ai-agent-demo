# Recording runbook

The final demo is one continuous, sanitized capture of three live browser
views, with native before/after evidence retained separately:

1. a configured synthetic Freshservice ticket before Cora acts;
2. Cora's real Clem/Codex terminal and the isolated-Civo AgentBus cockpit;
3. Cora's autonomously published private guidance in Freshservice;
4. optionally, the human's metadata-only approval note and the resulting tags.

Create the ignored `tmp/ssh/demo_config` with the Civo host, `civo` user,
disposable SSH key, and ignored known-hosts file. Keep the alias `gaidemo`; the
recording wrappers then hide the host, IP address, and username.

The dedicated Chrome profile exposes DevTools only on loopback port 9222. Once
the operator is logged in and the configured ticket is visible, capture the
content viewport without browser chrome or the desktop:

```bash
node recording/launch-browser.mjs TICKET_ID
node recording/prepare-demo-tabs.mjs TICKET_ID
DEMO_TICKET_ID=TICKET_ID node recording/chrome-cdp.mjs status
DEMO_TICKET_ID=TICKET_ID node recording/chrome-cdp.mjs screenshot \
  artifacts/live-demo/freshservice-before.png
```

After the autonomous note appears, capture Freshservice again. If metadata was
approved, include Cora's note, the human approval note, and all final tags in
the native frame:

```bash
node recording/capture-freshservice-tags.mjs \
  artifacts/live-demo/freshservice-after-tags.png TICKET_ID
```

Open the cockpit through the dedicated SSH tunnel in a second Chrome tab. It
must show Cora's intake, scoped reading, knowledge evidence, the autonomous
note result, and a metadata-only approval boundary from live AgentBus
deliveries. Open Cora's real terminal with:

```bash
recording/cora-console-tunnel.sh
node recording/capture-cora-console.mjs artifacts/live-demo/cora-console.webm 45
```

For the shortest product-owner narrative, stop after showing the private note:
the useful assistance arrived inside Freshservice without another approval UI.
For the full control narrative, let the human—not automation—add
`APPROVE AI <hash-prefix>` as a private Freshservice note, then show the
metadata tags being applied. The cockpit approval endpoint deliberately
returns HTTP 410.

Capture the isolated AgentBus audit chain through the one-time UI session. The
script obtains a session over SSH without copying or printing the admin token:

```bash
node recording/capture-live-agentbus.mjs \
  tmp/ssh/demo_config gaidemo \
  artifacts/live-demo/agentbus-live-full.png \
  artifacts/live-demo/agentbus-live-late.png
```

Assemble any ordered clips with:

```bash
recording/assemble-live-demo.sh artifacts/live-demo/final.mp4 \
  artifacts/live-demo/freshservice-before.mp4 \
  artifacts/live-demo/cora-console.webm \
  artifacts/live-demo/cockpit.webm \
  artifacts/live-demo/freshservice-after.mp4
```

## Safety

- Record only the synthetic tenant and configured ticket.
- Hide URLs, IPs, account menus, extensions, notifications, and identifying
  shell prompts.
- Never display `.env`, process environments, auth files, API keys, mailbox
  tokens, SSH keys, or browser cookies.
- Do not automate the optional human metadata approval.
- Do not present the older cockpit-click prototype or replayed AgentBus events
  as a live run.
