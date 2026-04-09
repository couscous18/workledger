# Reporting

The default report bundle writes:

- `summary.json`
- `cost_by_work_category.csv`
- `classification_traces.parquet`
- `summary.md`
- `summary.html`

The reports are meant to prove the ledger layer, not just echo the source trace.

They lead with trace-to-work sections:

- dataset context
- raw trace excerpt
- normalized observations
- rolled work units
- review-needed work

Then they show the downstream views that are already supported in the code:

- pending review queue from policy classification
- ambiguity summaries
- compression proof point
- top material work units
- cost by work category
- cost by policy outcome
- low-trust high-cost items
- downstream economics, only when enabled

## What The Reports Make Legible

The default bundle shows:

- how raw trace records were normalized into `ObservationSpan`
- how many observations were rolled into each `WorkUnit`
- which items still require review
- where blended cost is accumulating by category or policy outcome
- which costly items are still low-trust

`summary.json` contains the full structured summary, including totals, compression story, queue data, and cost slices.
`classification_traces.parquet` preserves the downstream attribution layer for local analysis.
`summary.md` and `summary.html` present the same narrative in human-readable form.

`wl report` does not include economics by default. Use `wl report --include-economics` when you want that secondary view.
That keeps the core report focused on attributed work while still making comparative economics a first-class supported option.
