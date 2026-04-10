# workledger

`workledger` is a Python CLI and local pipeline for turning AI trace inputs into normalized observations, rolled units of work, and optional downstream policy/reporting outputs.

In plain English: it helps you turn messy agent traces into human-reviewable units of work so you can understand what happened, what it cost, and what may need review.

![open traces before and after](assets/open-traces-before-after.svg)

The codebase is centered on three objects:

- `ObservationSpan`: normalized trace or span record
- `WorkUnit`: rolled work item with evidence, lineage, cost, and review state
- `ClassificationTrace`: optional policy-backed interpretation of a work unit

This repository is primarily a local DuckDB-backed pipeline exposed through the `wl` CLI. It also ships a FastAPI server, built-in YAML policy packs, benchmark fixtures, schema artifacts, synthetic demos, and two Hugging Face dataset adapters.

Start with the network-free local demo:

```bash
# prerequisites: Python 3.11+ and uv (https://docs.astral.sh/uv/getting-started/installation/)
git clone https://github.com/couscous18/workledger.git
cd workledger
uv sync --all-extras
uv run wl demo coding --project-dir .workledger/coding --open-report
```

Optional public-trace demos:

```bash
uv run wl demo hf-gaia --project-dir .workledger/hf-gaia --open-report
uv run wl demo hf-smoltrace --project-dir .workledger/hf-smoltrace --open-report
```

The Hugging Face demos exercise ingest, rollup, and reporting. Policy classification remains explicit.

Start here:

- [Getting Started](getting-started.md)
- [CLI Reference](cli.md)
- [How It Works](how-it-works.md)
- [Data Model](data-model.md)
- [Adapters & Integrations](adapters.md)
- [Reporting](reporting.md)
- [Public Traces Demo](public-traces-demo.md)
