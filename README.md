# workledger

[![CI](https://github.com/couscous18/workledger/actions/workflows/ci.yml/badge.svg)](https://github.com/couscous18/workledger/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://couscous18.github.io/workledger/)

`workledger` is the open trace-to-work layer for AI systems.

**Observability tells you what ran. `workledger` tells you what work happened.**

`workledger` turns raw traces, trajectories, and agent messages into `WorkUnit`s: the durable, reviewable primitive for understandable work, with preserved evidence and lineage.
Public traces are the easiest way to prove that in the open, starting with Hugging Face datasets such as [`smolagents/gaia-traces`](https://huggingface.co/datasets/smolagents/gaia-traces) and [`kshitijthakkar/smoltrace-traces-20260130_053009`](https://huggingface.co/datasets/kshitijthakkar/smoltrace-traces-20260130_053009).
Economics, policy, and accounting stay downstream of that core trace-to-work attribution layer.

```text
raw traces / messages / spans
  -> normalized ObservationSpan
  -> rolled-up WorkUnit
  -> review / policy / economics
```

## Quickstart

```bash
git clone https://github.com/couscous18/workledger.git
cd workledger
uv sync --all-extras

uv run wl demo hf-gaia --project-dir .workledger/hf-gaia --open-report
```

Optional second run:

```bash
uv run wl demo hf-smoltrace --project-dir .workledger/hf-smoltrace --open-report
```

Manual path from the same flagship dataset:

```bash
uv run wl ingest-hf smolagents/gaia-traces --adapter gaia --split train --limit 3 --seed 7 --project-dir .workledger/hf-gaia
uv run wl rollup --project-dir .workledger/hf-gaia
uv run wl report --project-dir .workledger/hf-gaia
```

PyPI is not live for this release, so the public install path is source-first from this repository.
The flagship path is [`smolagents/gaia-traces`](https://huggingface.co/datasets/smolagents/gaia-traces): public agent messages in, understandable `WorkUnit`s out.
[`kshitijthakkar/smoltrace-traces-20260130_053009`](https://huggingface.co/datasets/kshitijthakkar/smoltrace-traces-20260130_053009) is the telemetry-native proof that the same model works for trace-and-span datasets too.

![open traces before and after](docs/assets/open-traces-before-after.svg)

[Open Traces](docs/open-traces.md) · [Trace To Work](docs/trace-to-work.md) · [Public Traces Demo](docs/public-traces-demo.md) · [Getting Started](docs/getting-started.md) · [Docs](https://couscous18.github.io/workledger/)

## Before / After

Before:

- many raw messages, steps, spans, and tool calls
- plenty of observability detail
- unclear boundaries for the actual work

After:

- a few `WorkUnit`s with title, status, evidence, lineage, and review state
- review-needed items where the trace does not cleanly resolve
- optional downstream economics attached to accountable work instead of only raw requests or spans
- a stable seam for adapters across public trace formats

## The Missing Primitive

`WorkUnit` is the public primitive in `workledger`.

Tracing backends and observability tools are good at preserving execution detail.
`workledger` sits one layer above them and preserves the part people actually need to reason about: the work.

- `ObservationSpan` is the normalized execution record
- `WorkUnit` is the durable, human-readable unit of work
- evidence and lineage stay attached to that work
- review, policy, and economics are downstream interpretations on top of attributed work

## First-Class Public Datasets

Supported now:

- [`smolagents/gaia-traces`](https://huggingface.co/datasets/smolagents/gaia-traces)
  message / trajectory shape
- [`kshitijthakkar/smoltrace-traces-20260130_053009`](https://huggingface.co/datasets/kshitijthakkar/smoltrace-traces-20260130_053009)
  trace / spans / totals shape

Planned next:

- [`smolagents/codeagent-traces`](https://huggingface.co/datasets/smolagents/codeagent-traces)
  documented as a future adapter target, not yet implemented

## What `workledger` Is

- an open trace-to-work attribution layer and work ledger
- a bridge from public traces to `WorkUnit`
- a local-first pipeline for normalization, rollup, review, reporting, and cost attribution
- a small adapter seam for new trace ecosystems

## What `workledger` Is Not

- an APM product
- a tracing backend
- a generic eval framework
- a reasoning-trace viewer
- enterprise compliance software with OSS paint on top

## Why Builders Care

- many spans can become a few understandable `WorkUnit`s
- ambiguity stays visible instead of getting flattened into fake certainty
- evidence and lineage stay attached to each interpretation
- review queues and policy outcomes stay grounded in the rolled work
- public datasets become runnable demos instead of static artifacts
- economics remain available, but as a downstream lens, not the thesis

## CLI Surface

```bash
wl ingest traces.jsonl
wl ingest-hf smolagents/gaia-traces --adapter gaia --split train --limit 3 --seed 7
wl rollup
wl classify
wl report
wl demo hf-gaia
wl demo hf-smoltrace
wl compare-costs --from-project .workledger/hf-smoltrace
```

`wl report` no longer includes economics by default. Add `--include-economics` when you want that downstream view.

## Existing Downstream Paths

Synthetic demos, policy packs, comparative economics, and software capex review are still in the repo.
They are downstream examples of the same trace-to-work foundation, not the homepage story.

The compatibility demo alias `wl demo open-traces` still works for the original synthetic coding path.

## Development

```bash
make lint
make test
make docs
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for adapter and fixture guidance.
