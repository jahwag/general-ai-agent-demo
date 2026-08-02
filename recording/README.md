# Recording runbook

The final demo is a continuous, sanitized capture of two live browser tabs,
with native before/after evidence retained separately:

1. `freshworks-before.mp4`: synthetic ticket #2 before approval;
2. the Cora cockpit backed by the isolated Civo AgentBus, including the human
   click and approval-gateway result;
3. `freshworks-after.mp4`: refreshed ticket showing the private note and tags.

Before recording, create the ignored `tmp/ssh/demo_config` with the Civo host,
the `civo` user, the disposable SSH key, and the existing ignored known-hosts
file. Keep the alias name `gaidemo`; the VHS PATH intentionally resolves
`ssh gaidemo` through `recording/bin/ssh` so no host, IP address, or username is
shown in the video.

The dedicated Chrome profile exposes DevTools only on loopback port 9222. Once
the operator has logged in and ticket #2 is visible, capture the content
viewport—never the browser chrome or desktop—with:

```bash
node recording/chrome-cdp.mjs status
node recording/chrome-cdp.mjs screenshot artifacts/freshworks-before.png
recording/still-to-clip.sh artifacts/freshworks-before.png \
  artifacts/freshworks-before.mp4 15
```

After the single approved write, reload ticket #2 and repeat with `after` in
the filenames. The capture command refuses any page whose path is not ticket
#2. This hides the address bar, tenant URL, account menus, extensions, desktop
notifications, and unrelated tickets by construction. Then assemble:

```bash
recording/assemble.sh
```

## Live AI-led cockpit

Open `http://127.0.0.1:18765/` through the dedicated SSH tunnel as the second
Chrome tab. The cockpit reports Cora's intake, scoped reading, knowledge
evidence, proposal hash, pending human control, and the separately identified
operator-gateway result directly from AgentBus deliveries.

Start the screen capture while approval is still pending. Show Freshservice,
switch to the cockpit, let the human click `APPROVE LIVE PROPOSAL` and confirm
the hash-bound dialog once, wait for `Operator gateway` to turn green, then
switch back to Freshservice and reload it.

The older `record-cockpit.sh` path is retained only as a prototype reference. It
must not be presented as the live run.

```bash
ffmpeg -f x11grab -framerate 30 -video_size 1440x900 \
  -i :1.0+100,100 -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
  artifacts/live-demo/live-approval.mp4
```
