# Getting Started

`workledger` is an agent work ledger for AI systems. It turns raw trace exhaust into `WorkUnit`s you can inspect, review, classify, and compare economically.

## Install

```bash
git clone https://github.com/couscous18/workledger.git
cd workledger
uv sync --all-extras
uv run wl init --project-dir .workledger
```

> PyPI distribution is not live yet. Install from source for now.

## Quickstart: Agent Work Ledger

```bash
uv run wl demo agent-cost --project-dir .workledger/agent-cost --open-report
uv run wl compare-costs --from-project .workledger/agent-cost
```

This flagship path shows the core thesis fastest:

- many spans become a few understandable `WorkUnit`s
- expensive or low-trust work is surfaced
- ambiguous work lands in a review queue
- deployment economics are compared with transparent assumptions

## Explore More Demos

```bash
wl demo all --project-dir .workledger/demo --open-report
wl compare-costs --from-project .workledger/demo
```

Use this broader bundle if you want coding, marketing, and support examples after the flagship agent workflow.
