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

Capture only the Freshservice ticket content area for the browser clips. Hide
the address bar, tenant URL, account menus, extensions, desktop notifications,
and unrelated tickets. Then assemble:

```bash
recording/assemble.sh
```
