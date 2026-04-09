# Getting Started

`workledger` is an open trace-to-work layer for AI systems. It turns raw trace exhaust into `WorkUnit`s you can inspect, review, classify, and compare economically.

## Install

```bash
git clone https://github.com/couscous18/workledger.git
cd workledger
uv sync --all-extras
uv run wl init --project-dir .workledger
```

> PyPI publishing is coming. For now, install from source.

## Quickstart: Open Trace-to-Work

```bash
uv run wl demo open-traces --project-dir .workledger/open-traces --open-report
uv run wl compare-costs --from-project .workledger/open-traces
```

This flagship path shows the core thesis fastest:

- many spans become a few understandable `WorkUnit`s
- expensive or low-trust work is surfaced
- ambiguous work lands in a review queue
- deployment economics are compared with transparent assumptions
- the same open traces can support downstream public packaging and policy-backed interpretation

## Explore More Demos

```bash
wl demo all --project-dir .workledger/demo --open-report
wl compare-costs --from-project .workledger/demo
```

Use this broader bundle if you want coding, marketing, and support examples after the flagship agent workflow.
