# Getting Started

`workledger` turns traces into understandable work.

## Install

```bash
git clone https://github.com/couscous18/workledger.git
cd workledger
uv sync --all-extras
```

## Quickstart: Public Traces To Work

```bash
uv run wl demo hf-gaia --project-dir .workledger/hf-gaia --open-report
```

This is the flagship path:

- public Hugging Face messages in
- normalized observations out
- a few understandable `WorkUnit`s
- review-needed work where ambiguity remains

## Second Demo: Trace-Native Spans

```bash
uv run wl demo hf-smoltrace --project-dir .workledger/hf-smoltrace --open-report
```

This is the telemetry-native proof:

- many spans are not yet work
- explicit span hierarchy is preserved
- duration and cost remain attached
- rollup makes the trace legible

## Bring Your Own Public Dataset Sample

```bash
uv run wl ingest-hf smolagents/gaia-traces --adapter gaia --split train --limit 3 --seed 7 --project-dir .workledger/hf-gaia
uv run wl rollup --project-dir .workledger/hf-gaia
uv run wl report --project-dir .workledger/hf-gaia
```

## Existing Non-Public Paths

You can still use:

- `wl ingest` for JSON or JSONL traces
- `wl demo agent-cost` for the original synthetic coding demo
- `wl compare-costs` when you explicitly want downstream economics
