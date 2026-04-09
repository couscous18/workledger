# Public Traces Demo

This is the official public demo path for the repo.
It shows the core thesis in the open: many public traces are not yet understandable work, and `workledger` is the layer that rolls them into legible `WorkUnit`s.

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
- Dataset: [`smolagents/gaia-traces`](https://huggingface.co/datasets/smolagents/gaia-traces)

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
- Dataset: [`kshitijthakkar/smoltrace-traces-20260130_053009`](https://huggingface.co/datasets/kshitijthakkar/smoltrace-traces-20260130_053009)

## Before / After

![open traces before and after](assets/open-traces-before-after.svg)

The important change is not better observability.
It is trace-to-work attribution with `WorkUnit` as the primitive.
