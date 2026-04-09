# Reporting

The default report bundle writes:

- `summary.json`
- `cost_by_work_category.csv`
- `classification_traces.parquet`
- `summary.md`
- `summary.html`

The report now leads with trace-to-work sections:

- dataset context
- raw trace excerpt
- normalized observations
- rolled work units
- review-needed work

After that it can include:

- pending review queue from policy classification
- ambiguity summaries
- compression proof point
- downstream economics, only when enabled

`wl report` does not include economics by default. Use `wl report --include-economics` when you want that secondary view.
