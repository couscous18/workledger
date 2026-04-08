# Reporting

The default report bundle writes:

- `summary.json`
- `cost_by_work_category.csv`
- `classification_traces.parquet`
- `summary.md`
- `summary.html`

The HTML report is intended to be screenshot-friendly for internal review, demos, and shareable proof that many traces became a few understandable work units.

Common sections include:

- cost by policy outcome
- pending review queue
- top ambiguous items
- compression proof point
- low-trust high-cost outputs

When economics comparison is enabled, the report bundle also includes a comparative economics section that contrasts observed spend with transparent open-hosted and self-hosted assumptions.
