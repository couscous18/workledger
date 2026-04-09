# workledger

`workledger` is the open trace-to-work layer for AI systems.

**Observability tells you what ran. `workledger` tells you what work happened.**

![open traces before and after](assets/open-traces-before-after.svg)

Open-source AI is creating more public traces.
What is missing is an open way to attribute those traces to work.

`workledger` takes public traces, trajectories, and span trees and turns them into `WorkUnit`s: smaller units of work with evidence, lineage, and explicit review-needed states.

Start with the public trace path:

```bash
git clone https://github.com/couscous18/workledger.git && cd workledger
uv sync --all-extras
uv run wl demo hf-gaia --project-dir .workledger/hf-gaia --open-report
```

Then try the telemetry-native companion demo:

```bash
uv run wl demo hf-smoltrace --project-dir .workledger/hf-smoltrace --open-report
```

Use it when you want:

- an open bridge from traces to legible work
- Hugging Face public traces turned into runnable, reviewable demos
- adapter-friendly ingestion for new public trace formats
- preserved evidence and lineage instead of opaque aggregation
- economics as a downstream lens, not the lead story

Start here:

- [Open Traces](open-traces.md)
- [Trace To Work](trace-to-work.md)
- [Public Traces Demo](public-traces-demo.md)
- [Getting Started](getting-started.md)
- [CLI Reference](cli.md)
- [Comparative Economics](comparative-economics.md)
- [Software CapEx Review](software-capex.md)
