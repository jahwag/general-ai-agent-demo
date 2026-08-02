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
