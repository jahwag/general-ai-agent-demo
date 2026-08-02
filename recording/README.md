# Recording runbook

The final demo is one continuous, sanitized capture of two live browser tabs,
with native before/after evidence retained separately:

1. Freshservice synthetic ticket #2 before approval;
2. the observability cockpit backed by the isolated Civo AgentBus;
3. the human's real private approval note inside Freshservice;
4. the gateway result in both AgentBus and Freshservice.

Before recording, create the ignored `tmp/ssh/demo_config` with the Civo host,
`civo` user, disposable SSH key, and ignored known-hosts file. Keep the alias
`gaidemo`; the VHS path resolves `ssh gaidemo` through `recording/bin/ssh`, so
the video does not show a host, IP address, or username.

The dedicated Chrome profile exposes DevTools only on loopback port 9222. Once
the operator is logged in and ticket #2 is visible, capture the content viewport
without browser chrome or the desktop:

```bash
node recording/chrome-cdp.mjs status
node recording/chrome-cdp.mjs screenshot artifacts/freshworks-before.png
recording/still-to-clip.sh artifacts/freshworks-before.png \
  artifacts/freshworks-before.mp4 15
```

After the single approved write, reload ticket #2 and repeat with `after` in the
filenames. The capture command refuses any page whose path is not ticket #2.
This hides the address bar, tenant URL, account menus, extensions, desktop
notifications, and unrelated tickets by construction. Assemble with:

```bash
recording/assemble.sh
```

## Live native-approval flow

Open `http://127.0.0.1:18765/` through the dedicated SSH tunnel in a second
Chrome tab. The cockpit reports Cora's intake, scoped reading, knowledge
evidence, proposal hash, pending human control, authenticated approval, and
gateway result from live AgentBus deliveries.

Start screen capture while approval is pending. Show Freshservice, switch to the
cockpit to explain the work and copy the exact `APPROVE AI <hash-prefix>` value,
then switch back to Freshservice. The human—not automation—adds that value as a
private note. Return to the cockpit for the watcher and gateway events, then
reload Freshservice for the solution note and tags.

The cockpit approval endpoint deliberately returns HTTP 410. Do not present the
older cockpit-click prototype or an AgentBus replay as the live run.

```bash
ffmpeg -f x11grab -framerate 30 -video_size 1440x900 \
  -i :1.0+100,100 -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
  artifacts/live-demo/live-approval.mp4
```
