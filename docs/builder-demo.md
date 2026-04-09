# Builder Demo

This page keeps the original synthetic builder demo for local, offline exploration.

If you want the official public OSS story, start with:

- [Public Traces Demo](public-traces-demo.md)
- [Open Traces](open-traces.md)

The synthetic builder path is still useful when you want a deterministic local demo with no external dataset dependency:

```bash
uv run wl demo agent-cost --project-dir .workledger/agent-cost --open-report
```

Optional follow-up economics view:

```bash
uv run wl compare-costs --from-project .workledger/agent-cost
```

Treat it as a compatibility demo, not the lead public narrative.
