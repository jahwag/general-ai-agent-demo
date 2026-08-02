# AI-led service desk cockpit — throwaway UI prototype

Question: which read-only surface best communicates that the AI drives ticket intake,
research, and proposal drafting while a human approval and operator-owned gateway
remain the only path to a Freshservice write?

The three deliberately different variants are replayed from the verified synthetic
ticket #1 run. They do not call Freshservice or perform mutations.

Run from the repository root:

```bash
recording/cockpit-prototype/serve.sh
```

Then open:

- `http://127.0.0.1:8765/recording/cockpit-prototype/?variant=A`
- `http://127.0.0.1:8765/recording/cockpit-prototype/?variant=B`
- `http://127.0.0.1:8765/recording/cockpit-prototype/?variant=C`

Use the floating switcher or left/right arrow keys. Add `&autoplay=1&record=1`
to run the selected variant as a clean recording replay.

