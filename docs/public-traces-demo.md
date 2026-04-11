# Public Traces Demo

This is the optional public-trace path in the repo. It demonstrates the implemented Hugging Face adapters and shows how public rows become normalized observations and rolled work units.

## GAIA Messages

Run:

```bash
uv run wl demo hf-gaia --project-dir .workledger/hf-gaia --open-report
```

This demo uses the `gaia` adapter and shows:

- raw messages in
- normalized observations
- a few rolled `WorkUnit`s
- preserved Hugging Face lineage refs

By default this demo does not run `wl classify`.

Artifact:

- [GAIA demo report](assets/hf-gaia-demo-report.html)
- Dataset: [`smolagents/gaia-traces`](https://huggingface.co/datasets/smolagents/gaia-traces)

## smoltrace Spans

Run:

```bash
uv run wl demo hf-smoltrace --project-dir .workledger/hf-smoltrace --open-report
```

This demo uses the `smoltrace` adapter and leans into native span hierarchy:

- `trace_id + spans` ingestion
- duration and cost totals preserved
- rollup from many spans to understandable work

Artifact:

- [smoltrace demo report](assets/hf-smoltrace-demo-report.html)
- Dataset: [`kshitijthakkar/smoltrace-traces-20260130_053009`](https://huggingface.co/datasets/kshitijthakkar/smoltrace-traces-20260130_053009)

## Before / After

![open traces before and after](assets/open-traces-before-after.svg)

The important change is not better observability.
It is normalization plus rollup, with `WorkUnit` as the main output.

If you want policy output after running a public demo, run classification explicitly:

```bash
uv run wl classify --project-dir .workledger/hf-gaia
uv run wl report --project-dir .workledger/hf-gaia
```
