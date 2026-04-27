# Reporting

`wl report` writes a fixed report bundle into the project `reports/` directory:

- `summary.json`
- `cost_by_work_category.csv`
- `classification_traces.parquet`
- `summary.md`
- `summary.html`

The report engine reads from the local DuckDB store. It can render useful output after ingest and rollup alone, but some sections only populate after classification.

## Sections The Reports Generate Today

Always available when data exists:

- dataset context
- raw trace excerpt
- normalized observations
- rolled work units
- review-needed work

Available after `wl classify` has produced `ClassificationTrace` rows:

- pending review queue from policy classification
- ambiguity summaries
- compression proof point
- top material work units
- cost by policy outcome
- cost by work category
- low-trust high-cost items

Available only when `--include-economics` is passed:

- comparative economics

## Other Output Surfaces

- `wl report` also renders a terminal summary
- `wl export` can export any known table as CSV, Parquet, or JSON
- `wl explain` prints a stored work unit or classification as JSON

## What The Reports Make Legible

The current bundle is designed to show:

- how raw trace records were normalized into `ObservationSpan`
- how many observations were rolled into each `WorkUnit`
- which items still require review
- where blended cost is accumulating by category or policy outcome
- which costly items are still low-trust

`summary.json` contains the full structured summary, including totals, compression story, queue data, and cost slices.
`classification_traces.parquet` preserves the downstream attribution layer for local analysis.
`summary.md` and `summary.html` present the same narrative in human-readable form.

`classification_traces.parquet` is still written even if you have not classified anything yet; in that case it simply reflects the empty downstream layer.
