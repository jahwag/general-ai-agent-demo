# Recording runbook

The final demo is one continuous, sanitized capture of three live browser views,
with native before/after evidence retained separately:

1. Freshservice configured synthetic ticket before approval;
2. the observability cockpit backed by the isolated Civo AgentBus;
3. the human's real private approval note inside Freshservice;
4. the gateway result in both AgentBus and Freshservice.

Before recording, create the ignored `tmp/ssh/demo_config` with the Civo host,
`civo` user, disposable SSH key, and ignored known-hosts file. Keep the alias
`gaidemo`; the VHS path resolves `ssh gaidemo` through `recording/bin/ssh`, so
the video does not show a host, IP address, or username.

The dedicated Chrome profile exposes DevTools only on loopback port 9222. Once
the operator is logged in and the configured ticket is visible, capture the content viewport
without browser chrome or the desktop:

```bash
node recording/launch-browser.mjs 3
node recording/prepare-demo-tabs.mjs 3
DEMO_TICKET_ID=3 node recording/chrome-cdp.mjs status
DEMO_TICKET_ID=3 node recording/chrome-cdp.mjs screenshot artifacts/freshworks-before.png
recording/still-to-clip.sh artifacts/freshworks-before.png \
  artifacts/freshworks-before.mp4 15
```

After the single approved write, reload the configured ticket and repeat with `after` in the
filenames. Set `DEMO_TICKET_ID` to the configured numeric ticket ID; the capture
command refuses any other ticket path.
This hides the address bar, tenant URL, account menus, extensions, desktop
notifications, and unrelated tickets by construction. After approval, capture
the two agent identities and all tags in one native Freshservice frame:

```bash
node recording/capture-freshservice-tags.mjs \
  artifacts/live-demo/freshservice-after-tags.png 3
```

Assemble with:

```bash
recording/assemble.sh
```

For the full Cora → cockpit → Freshservice → raw AgentBus sequence, pass any
number of ordered clips to the flexible assembler:

```bash
recording/assemble-live-demo.sh artifacts/live-demo/final.mp4 \
  artifacts/live-demo/freshservice-before.mp4 \
  artifacts/live-demo/cora-console.webm \
  artifacts/live-demo/cockpit.webm \
  artifacts/live-demo/freshservice-after.mp4
```

## Live native-approval flow

Open `http://127.0.0.1:18765/` through the dedicated SSH tunnel in a second
Chrome tab. The cockpit reports Cora's intake, scoped reading, knowledge
evidence, proposal hash, pending human control, authenticated approval, and
gateway result from live AgentBus deliveries.

Open Cora's real, read-only Clem/Codex terminal on `http://127.0.0.1:17681/`:

```bash
recording/cora-console-tunnel.sh
node recording/capture-cora-console.mjs artifacts/cora-console.webm 45
```

Start screen capture while approval is pending. Show Freshservice, switch to the
cockpit to explain the work and copy the exact `APPROVE AI <hash-prefix>` value,
then switch back to Freshservice. The human—not automation—adds that value as a
private note. Return to the cockpit for the watcher and gateway events, then
reload Freshservice for the solution note and tags.

The cockpit approval endpoint deliberately returns HTTP 410. Do not present the
older cockpit-click prototype or an AgentBus replay as the live run.

Capture the isolated live AgentBus audit chain through a one-time UI session;
the script obtains the session over SSH without copying or printing the admin
token:

```bash
node recording/capture-live-agentbus.mjs \
  tmp/ssh/demo_config gaidemo \
  artifacts/live-demo/agentbus-live-full.png \
  artifacts/live-demo/agentbus-live-late.png
```

```bash
ffmpeg -f x11grab -framerate 30 -video_size 1440x900 \
  -i :1.0+100,100 -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
  artifacts/live-demo/live-approval.mp4
```
