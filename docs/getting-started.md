# Getting Started

`workledger` is the open trace-to-work layer for AI systems. It turns public traces into understandable `WorkUnit`s.

## Install

```bash
git clone https://github.com/couscous18/workledger.git
cd workledger
uv sync --all-extras
```

PyPI is not live for this release. Install from source from this repository.

## Official First Run: `hf-gaia`

```bash
uv run wl demo hf-gaia --project-dir .workledger/hf-gaia --open-report
```

This is the flagship path:

- public Hugging Face messages in
- normalized observations out
- a few understandable `WorkUnit`s
- review-needed work where ambiguity remains

## Optional Second Run: `hf-smoltrace`

```bash
uv run wl demo hf-smoltrace --project-dir .workledger/hf-smoltrace --open-report
```

This is the telemetry-native proof:

- many spans are not yet work
- explicit span hierarchy is preserved
- duration and cost remain attached
- rollup makes the trace legible

## Manual Path From The Same Dataset

```bash
uv run wl ingest-hf smolagents/gaia-traces --adapter gaia --split train --limit 3 --seed 7 --project-dir .workledger/hf-gaia
uv run wl rollup --project-dir .workledger/hf-gaia
uv run wl report --project-dir .workledger/hf-gaia
```

`wl report` does not include economics by default. Add `--include-economics` when you want that downstream view.

## Existing Compatibility Paths

You can still use:

- `wl ingest` for JSON or JSONL traces
- `wl demo open-traces` as a compatibility alias for the original synthetic coding demo
- `wl demo agent-cost` as the older synthetic demo name
- `wl compare-costs` when you explicitly want downstream economics
