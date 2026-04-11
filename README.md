# workledger

[![CI](https://github.com/couscous18/workledger/actions/workflows/ci.yml/badge.svg)](https://github.com/couscous18/workledger/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://couscous18.github.io/workledger/)

`workledger` is a Python CLI and local pipeline for turning AI trace data into normalized observations, rolled units of work, and optional policy, review, report, and cost-analysis outputs.

In plain English: it helps you turn messy agent traces into human-reviewable units of work so you can see what happened, what it cost, and what may need review.

The core implemented flow today is:

- `ObservationSpan`: normalized trace/message/span record
- `WorkUnit`: rolled-up unit of work with evidence, lineage, review state, and cost
- `ClassificationTrace`: optional policy-backed interpretation of a `WorkUnit`

The repository is source-first and alpha. It primarily ships a local DuckDB-backed pipeline, plus a FastAPI server, JSON Schema/OpenAPI artifacts, small observation emitters, synthetic demos, and two Hugging Face dataset adapters.

```text
JSON / JSONL / OpenInference / OTEL / CloudEvents / SDK events / supported HF datasets
  -> ObservationSpan
  -> WorkUnit
  -> optional ClassificationTrace
  -> reports / review queue / exports / comparative economics
```

## What This Repo Contains

- `src/workledger/`: the main pipeline, models, ingestion, rollup, policy, reporting, storage, review, and economics code
- `src/workledger_server/`: a FastAPI wrapper around the same local pipeline
- `src/workledger_observe/`: helpers for emitting canonical observation events
- `policies/`: built-in YAML policy packs
- `benchmark-data/`: a labeled benchmark suite for the software capex policy pack
- `examples/`: tiny and framework-oriented examples
- `schemas/`: generated JSON Schema and OpenAPI artifacts

## Core Primitive

`WorkUnit` is the main object this repository introduces.

`ObservationSpan` is the ingestion boundary. It preserves source trace identity, timestamps, token counts, direct cost, lineage, and source-specific metadata.

`WorkUnit` is the rollup boundary. It groups related observations into something a human can inspect: title, summary, objective, evidence bundle, lineage refs, source span IDs, review/trust state, and rolled cost.

`ClassificationTrace` is downstream of that. It attaches rule-based policy outcomes, confidence, evidence strength, and review requirements to an already-rolled `WorkUnit`.

## Recommended First Run

The best no-network end-to-end path in the repo is the local coding demo:

```bash
# prerequisites: Python 3.11+ and uv (https://docs.astral.sh/uv/getting-started/installation/)
git clone https://github.com/couscous18/workledger.git
cd workledger
uv sync --all-extras

uv run wl demo coding --project-dir .workledger/coding --open-report
```

That command:

- writes synthetic SDK-style observation events into `.workledger/coding/raw/`
- ingests them into a local DuckDB project
- rolls them into `WorkUnit`s
- classifies them with the built-in management reporting policy pack
- writes terminal, JSON, CSV, Parquet, Markdown, and HTML report outputs
- prints the generated HTML report path when `--open-report` is set

If you want the smallest Python example instead of the full CLI flow:
```bash
uv run python examples/tiny_pipeline.py
```

For a broader local demo bundle after the coding path:

```bash
uv run wl demo all --project-dir .workledger/demo --open-report
uv run wl compare-costs --from-project .workledger/demo
```

To bring your own traces:

```bash
uv run wl init --project-dir .workledger/my-traces
uv run wl ingest your-traces.json --project-dir .workledger/my-traces
uv run wl rollup --project-dir .workledger/my-traces
uv run wl classify --project-dir .workledger/my-traces
uv run wl report --project-dir .workledger/my-traces
```

Supported formats: `otel`, `openinference`, `jsonl`, `cloudevents`, `sdk`

## Optional Public Trace Demos

The repo also includes optional Hugging Face ingestion for two implemented dataset shapes:

```bash
uv run wl ingest-hf smolagents/gaia-traces --adapter gaia --split train --limit 3 --seed 7 --project-dir .workledger/hf-gaia
uv run wl rollup --project-dir .workledger/hf-gaia
uv run wl report --project-dir .workledger/hf-gaia

uv run wl ingest-hf kshitijthakkar/smoltrace-traces-20260130_053009 --adapter smoltrace --split train --limit 3 --seed 7 --project-dir .workledger/hf-smoltrace
uv run wl rollup --project-dir .workledger/hf-smoltrace
uv run wl report --project-dir .workledger/hf-smoltrace
```

Or via demos:

```bash
uv run wl demo hf-gaia --project-dir .workledger/hf-gaia --open-report
uv run wl demo hf-smoltrace --project-dir .workledger/hf-smoltrace --open-report
```

Important: the Hugging Face demos ingest, roll up, and report by default. They do **not** automatically run policy classification unless you explicitly run `wl classify` afterward or pass a policy into the underlying demo helper.

## Inputs Supported Today

`wl ingest` supports `.json` and `.jsonl` files containing:

- canonical SDK-shaped observation events
- OpenInference-like payloads with `trace_id` / `span_id`
- OTEL-style JSON spans with `traceId` / `spanId`
- CloudEvents whose `data` contains either canonical SDK payloads or OpenInference-like payloads

`wl ingest-hf` supports only these implemented adapters:

- `gaia` for message-style rows such as [`smolagents/gaia-traces`](https://huggingface.co/datasets/smolagents/gaia-traces)
- `smoltrace` for trace-and-span rows such as [`kshitijthakkar/smoltrace-traces-20260130_053009`](https://huggingface.co/datasets/kshitijthakkar/smoltrace-traces-20260130_053009)

The REST API exposes the same ingestion boundary through `/ingest/events` and `/ingest/spans`.

## Outputs Produced Today

- terminal summaries and tables from `wl rollup`, `wl classify`, `wl report`, `wl review-queue`, and `wl compare-costs`
- report bundle files:
  - `summary.json`
  - `cost_by_work_category.csv`
  - `classification_traces.parquet`
  - `summary.md`
  - `summary.html`
- table exports to CSV, Parquet, or JSON via `wl export`
- review queue items and reviewer overrides
- benchmark reports in JSON or Markdown
- JSON Schema and OpenAPI artifacts under `schemas/`

## Main Workflows

1. Initialize a local project with `wl init`.
2. Ingest local trace payloads with `wl ingest`, or ingest supported public datasets with `wl ingest-hf`.
3. Roll low-level observations into `WorkUnit`s with `wl rollup`.
4. Optionally classify those work units with a YAML policy pack via `wl classify`.
5. Generate reports, exports, review queues, overrides, and cost comparisons from the local store.
6. Use `wl benchmark` to evaluate a policy pack against the included labeled suite.

## Repo Shape

This repository is primarily:

- a CLI tool (`wl`)
- a local trace-processing pipeline (`WorkledgerPipeline`)
- a schema/model package around `ObservationSpan`, `WorkUnit`, and `ClassificationTrace`
- a reporting and review layer on top of a local DuckDB store

It also includes:

- a small FastAPI server
- a benchmark harness for policy packs
- synthetic demos and example integrations
- tiny helper packages for emitting canonical observation events

## What `workledger` Is

- a local trace-to-work pipeline
- a way to normalize heterogeneous trace payloads into one schema
- a rollup engine that groups observations into higher-level work units
- a policy/reporting layer built on top of those rolled work units

## What `workledger` Is Not

- a tracing backend
- an APM product
- a general-purpose evaluation framework
- a hosted service in this repository
- a claim that policy or economics are the primary primitive

## Implemented vs Planned

Implemented today:

- local project initialization, storage, and schema export
- ingestion from local JSON/JSONL payloads
- Hugging Face adapters for GAIA-style message traces and smoltrace-style span traces
- rollup into `WorkUnit`
- YAML policy classification, review queue ranking, and overrides
- report generation, table export, comparative economics, benchmark evaluation, and a local API
- synthetic demos for coding, marketing, support, and the older `capex` alias

Planned or explicitly not live yet:

- more public dataset adapters such as `smolagents/codeagent-traces`
- package distribution on PyPI
- stable interfaces; the repo is still marked alpha

## Developer Surface

```bash
wl init
wl ingest traces.jsonl
wl ingest-hf <dataset-id> --adapter auto --split train --limit 3 --seed 7
wl rollup
wl classify
wl report
wl report --include-economics
wl review-queue
wl compare-costs --from-project .workledger/coding
wl benchmark benchmark-data/software_capex_review_v1 --format markdown
wl demo coding
wl demo hf-gaia
```

`wl report` only includes comparative economics when you pass `--include-economics`.

## Development

```bash
make lint
make test
make docs
```

PyPI is not live for this release, so installation is source-first from this repository.

![open traces before and after](docs/assets/open-traces-before-after.svg)

[Getting Started](docs/getting-started.md) · [CLI Reference](docs/cli.md) · [How It Works](docs/how-it-works.md) · [Data Model](docs/data-model.md) · [Docs](https://couscous18.github.io/workledger/)
