# Getting Started

`workledger` is installable as `workledger` on PyPI once the tagged release publish completes. The easiest way to understand the repo is to run a local end-to-end demo, then optionally try the supported public-trace adapters.

In plain English: the goal is to turn raw AI trace data into a smaller set of work items a person can inspect, review, and report on.

## Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)

## Install

If the package is already visible on PyPI:

```bash
python -m pip install workledger
```

If you are working from the repository directly or the first publish has not completed yet:

```bash
git clone https://github.com/couscous18/workledger.git
cd workledger
uv sync --all-extras
```

## Recommended First Run: Local Coding Demo

```bash
uv run wl demo coding --project-dir .workledger/coding --open-report
```

This path exercises the full CLI pipeline without requiring network access:

- synthetic SDK-style observation events
- ingest into the local DuckDB project
- rollup into multiple `WorkUnit`s
- policy classification
- report bundle generation
- review queue and comparative economics sections

You should end up with:

- a local database at `.workledger/coding/workledger.duckdb`
- raw inputs under `.workledger/coding/raw/`
- reports under `.workledger/coding/reports/`

## Optional Smallest Python Example

```bash
uv run python examples/tiny_pipeline.py
```

This runs the same pipeline from Python instead of through the CLI.

## Optional Public Trace Demos

### GAIA Messages

```bash
uv run wl demo hf-gaia --project-dir .workledger/hf-gaia --open-report
```

Uses the implemented `gaia` Hugging Face adapter for message-style rows such as `smolagents/gaia-traces`.

### smoltrace Spans

```bash
uv run wl demo hf-smoltrace --project-dir .workledger/hf-smoltrace --open-report
```

Uses the implemented `smoltrace` Hugging Face adapter for trace-and-span rows such as `kshitijthakkar/smoltrace-traces-20260130_053009`.

Important: both Hugging Face demos stop at ingest, rollup, and reporting by default. If you want a policy view after running one, do this explicitly:

```bash
uv run wl classify --project-dir .workledger/hf-gaia
uv run wl report --project-dir .workledger/hf-gaia
```

## Manual CLI Path

```bash
uv run wl init --project-dir .workledger/manual
uv run wl ingest tests/fixtures/openinference_support.jsonl --project-dir .workledger/manual
uv run wl rollup --project-dir .workledger/manual
uv run wl classify --project-dir .workledger/manual
uv run wl report --project-dir .workledger/manual
```

That fixture is included in the repository. `wl ingest` accepts `.json` and `.jsonl` if you want to substitute your own file.

`wl report` does not include comparative economics by default. Add `--include-economics` when you want that secondary view.

## Compatibility And Older Paths

You can still use:

- `wl ingest` for local JSON or JSONL payloads
- `wl demo open-traces` as a compatibility alias for the original synthetic coding demo
- `wl demo agent-cost` as the older synthetic demo name
- `wl compare-costs` when you explicitly want scenario-based cost estimates
