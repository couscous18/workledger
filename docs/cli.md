# CLI Reference

`wl` is the main public entrypoint for this repository.

## Core Lifecycle

```bash
wl init
wl ingest traces.jsonl
wl ingest-hf <dataset-id> --adapter auto --split train --limit 3 --seed 7
wl rollup
wl classify
wl report
wl report --include-economics
wl review-queue
wl override <classification-id> --reviewer <name> --note <text>
wl compare-costs --from-project .workledger/hf-smoltrace
wl explain <id>
wl export classification_traces parquet out/classification_traces.parquet
wl benchmark benchmark-data/software_capex_review_v1 --format markdown
```

## Command Notes

- `wl init`: create a local project directory and copy built-in policy packs
- `wl ingest`: load `.json` or `.jsonl` payloads and normalize them into `ObservationSpan`
- `wl ingest-hf`: load a supported Hugging Face dataset through an implemented adapter
- `wl rollup`: roll stored observations into `WorkUnit`
- `wl classify`: apply a YAML policy pack; defaults to `management_reporting_v1.yaml`
- `wl report`: write `summary.json`, `cost_by_work_category.csv`, `classification_traces.parquet`, `summary.md`, and `summary.html`
- `wl review-queue`: show pending review items ranked by priority
- `wl override`: apply a reviewer override to a stored classification
- `wl compare-costs`: estimate alternative scenario costs from observed token usage and direct cost
- `wl explain`: print the stored JSON for a work unit or classification
- `wl export`: export a store table as CSV, Parquet, or JSON
- `wl benchmark`: evaluate a policy pack against the included benchmark suite
- `wl doctor`: check local module and project setup

## Demos

Recommended local first run:

```bash
wl demo coding --project-dir .workledger/coding --open-report
```

Optional public-trace demos:

```bash
wl demo hf-gaia --project-dir .workledger/hf-gaia --open-report
wl demo hf-smoltrace --project-dir .workledger/hf-smoltrace --open-report
```

The Hugging Face demos ingest, roll up, and report. They do not classify by default.

Compatibility and broader demo paths:

```bash
wl demo open-traces  # compatibility alias for the original synthetic coding demo
wl demo agent-cost   # older name for that same synthetic path
wl demo capex
wl demo marketing
wl demo support
wl demo all
```

## Policy Commands

```bash
wl policies list
wl policies validate policies/management_reporting_v1.yaml
```
