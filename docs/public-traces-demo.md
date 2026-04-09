# Public Traces Demo

This is the official demo path for the repo.

It makes one point clear:

Many public traces are not yet understandable work.
`workledger` is the missing layer between those traces and legible `WorkUnit`s.

## Flagship Demo: `smolagents/gaia-traces`

Run:

```bash
uv run wl demo hf-gaia --project-dir .workledger/hf-gaia --open-report
```

This demo uses public message traces and shows:

- raw messages in
- normalized observations
- a few rolled `WorkUnit`s
- review-needed work where the trace is ambiguous
- preserved Hugging Face lineage refs

Artifact:

- [GAIA demo report](assets/hf-gaia-demo-report.html)

## Telemetry-Native Demo: `smoltrace`

Run:

```bash
uv run wl demo hf-smoltrace --project-dir .workledger/hf-smoltrace --open-report
```

This demo leans into native span hierarchy:

- `trace_id + spans` ingestion
- duration and cost totals preserved
- rollup from many spans to understandable work

Artifact:

- [smoltrace demo report](assets/hf-smoltrace-demo-report.html)

## Before / After

![open traces before and after](assets/open-traces-before-after.svg)

The important change is not better observability.
It is trace-to-work attribution.
