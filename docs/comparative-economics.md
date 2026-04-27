# Comparative Economics

Comparative economics is implemented, but it is downstream of ingest and rollup.

The command surface is:

```bash
wl compare-costs --from-project .workledger/coding
```

The report surface is:

```bash
wl report --include-economics
```

## What It Uses

- observed `token_input` and `token_output` on stored `ObservationSpan`
- observed direct cost on spans when present
- rolled `WorkUnit` counts and cost totals
- `ClassificationTrace` rows when available, to enrich per-category breakdowns

Classification improves the breakdowns, but it is not required for the command to run.

## Scenario Presets In Code

- `proprietary_api`
- `open_hosted`
- `self_hosted_gpu`

You can override the first scenario's rates from the CLI.

## What It Does Not Do

- it does not measure quality or task success
- it does not include latency, on-call, eval, or utilization waste unless modeled as overhead
- it does not replace the observed cost already present in the trace data

It is an estimate layer built on top of the ledger, not the core primitive itself.
