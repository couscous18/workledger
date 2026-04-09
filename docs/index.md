# workledger

`workledger` is the open trace-to-work layer for AI systems.

**Observability tells you what ran. `workledger` tells you what work happened.**

![open traces before and after](assets/open-traces-before-after.svg)

`workledger` takes raw traces, trajectories, and span trees and turns them into `WorkUnit`s: the durable primitive for understandable work, with evidence, lineage, and review state preserved.
The flagship path starts from public Hugging Face traces, with economics and policy kept as downstream interpretations after the work has already been attributed.

Start with the public trace path:

```bash
git clone https://github.com/couscous18/workledger.git
cd workledger
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
- visible review-needed states instead of fake certainty
- downstream economics built on top of attributed work instead of leading the story

Start here:

- [Getting Started](getting-started.md)
- [Public Traces Demo](public-traces-demo.md)
- [Open Traces](open-traces.md)
- [Trace To Work](trace-to-work.md)
- [CLI Reference](cli.md)
- [Comparative Economics](comparative-economics.md)
- [Software CapEx Review](software-capex.md)
