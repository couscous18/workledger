# workledger

`workledger` is an open trace-to-work layer for AI systems.

**Observability tells you what ran. `workledger` tells you what work happened.**

![workledger before and after](assets/workledger-before-after.svg)

`workledger` introduces `WorkUnit` as the missing layer between span-level telemetry and the decisions teams actually need to make. It compresses raw traces into accountable units of work with evidence, review states, and transparent economics.

If you only try one thing, run:

```bash
git clone https://github.com/couscous18/workledger.git && cd workledger
uv sync --all-extras
uv run wl demo open-traces --project-dir .workledger/open-traces --open-report
uv run wl compare-costs --from-project .workledger/open-traces
```

PyPI is not published yet. The source-install path above is the only public install path we should advertise right now.

![workledger demo screenshot](assets/workledger-demo-screenshot.png)

Use it when you already have traces and want:

- business-level work units instead of span soup
- evidence-backed cost rollups
- explainable work classifications and policy outcomes
- review queues for ambiguous work instead of fake certainty
- side-by-side economics estimates for proprietary, open-hosted, and self-hosted assumptions
- a public story that starts from open traces instead of opaque agent claims

Principles:

- compress noise into accountable work
- preserve uncertainty instead of overstating certainty
- keep evidence and lineage attached to interpretation
- separate observed facts from modeled assumptions
- stay open, inspectable, and local-first

Start here:

- [Proof Artifact](assets/builder-demo-report.html)
- [Release Notes v0.1.0](releases/v0.1.0.md)
- [Builder Demo](builder-demo.md)
- [Getting Started](getting-started.md)
- [How It Works](how-it-works.md)
- [Comparative Economics](comparative-economics.md)
- [Software CapEx Review](software-capex.md)
