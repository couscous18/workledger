# Comparative Economics

WorkLedger measures AI work directly and estimates alternative deployment economics transparently.

## What WorkLedger Measures

- observed input and output token counts
- observed direct inference cost when traces provide it
- work-unit and classification context

## What WorkLedger Estimates

`wl compare-costs` estimates what the same workload might cost under configurable scenarios such as:

- proprietary API
- open hosted inference
- self-hosted GPU inference

These estimates are derived from token totals plus editable assumptions. They are not benchmark claims.

## Important Caveat

“Self-hosted is cheaper” is not universally true. It depends on utilization, batching efficiency, operator overhead, GPU reservation waste, latency targets, and model quality requirements.
