# workledger

`workledger` is the open work ledger for AI systems.

**Observability tells you what ran. `workledger` tells you what work happened.**

![open traces before and after](assets/open-traces-before-after.svg)

`workledger` takes traces, trajectories, and span trees and turns them into `WorkUnit`s: durable units of work with evidence, lineage, review states, and cost attached.

Public traces are the easiest place to prove this in the open, but the product story is broader:

- work attribution that turns execution detail into legible work
- preserved evidence and lineage for every interpretation
- visible ambiguity and review-needed states instead of fake certainty
- cost attribution attached to work, not only spans
- downstream policy and economics once the work has been attributed

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

- an open bridge from traces to accountable work
- Hugging Face public traces turned into runnable, reviewable demos
- adapter-friendly ingestion for new trace formats
- preserved evidence, lineage, and work boundaries instead of opaque aggregation
- cost, review, and policy attached to rolled work
- economics as a downstream lens built on top of attributed work

Start here:

- [Open Traces](open-traces.md)
- [Trace To Work](trace-to-work.md)
- [Public Traces Demo](public-traces-demo.md)
- [Getting Started](getting-started.md)
- [CLI Reference](cli.md)
- [Comparative Economics](comparative-economics.md)
- [Software CapEx Review](software-capex.md)
