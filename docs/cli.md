# CLI Reference

`wl` is the main operator surface.

```bash
wl init
wl ingest traces.jsonl
wl rollup
wl classify
wl report
wl demo open-traces
wl demo all
wl compare-costs --from-project .workledger/open-traces
wl review-queue
wl benchmark benchmark-data/software_capex_review_v1 --format markdown
wl explain <id>
wl export classification_traces parquet out/classification_traces.parquet
wl doctor
```

For the flagship path, start with `wl demo open-traces --project-dir .workledger/open-traces --open-report`.

For the broader multi-team bundle, use `wl demo all --project-dir .workledger/demo --open-report`.

To compare observed spend with open-model assumptions, use `wl compare-costs --from-project .workledger/open-traces` or point it at any project directory you generated reports for.
