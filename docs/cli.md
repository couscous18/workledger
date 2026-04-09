# CLI Reference

The public-traces path is now the main `wl` surface.

```bash
wl ingest-hf smolagents/gaia-traces --adapter gaia --split train --limit 3 --seed 7
wl rollup
wl report
wl demo hf-gaia
wl demo hf-smoltrace
```

Core commands:

```bash
wl init
wl ingest traces.jsonl
wl ingest-hf <dataset-id> --adapter auto --split train --limit 3 --seed 7
wl rollup
wl classify
wl report
wl report --include-economics
wl review-queue
wl compare-costs --from-project .workledger/hf-smoltrace
wl explain <id>
wl export classification_traces parquet out/classification_traces.parquet
wl doctor
```

Flagship demo:

```bash
wl demo hf-gaia --project-dir .workledger/hf-gaia --open-report
```

Telemetry-native demo:

```bash
wl demo hf-smoltrace --project-dir .workledger/hf-smoltrace --open-report
```

Compatibility paths remain available:

```bash
wl demo open-traces
wl demo agent-cost
wl demo all
wl benchmark benchmark-data/software_capex_review_v1 --format markdown
```
