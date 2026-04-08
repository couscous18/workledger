# Builder Demo

`workledger` clicks fastest when you treat it as an agent work ledger, not a tracing dashboard.

![workledger before and after](assets/workledger-before-after.svg)

The flagship demo uses the bundled coding-agent events and shows the core proof:

- `14` source spans
- `3` work units
- `1` pending review item
- `1.56x` average compression from spans to work units

The important contrast is not just cost visibility. It is that the same raw telemetry becomes a ledger of work a human can reason about:

- a maintenance incident compresses into one accountable unit of work
- a product feature surfaces as meaningful but still not automatically trusted
- an ambiguous internal automation task lands in the review queue instead of being over-claimed

See the shareable proof artifact first:

- [Open the static builder demo report](assets/builder-demo-report.html)

Run the flagship path locally:

```bash
wl init --project-dir .workledger
wl demo agent-cost --project-dir .workledger/agent-cost --open-report
wl compare-costs --from-project .workledger/agent-cost
```

You should see:

- `3` work units with cost, evidence, and trust context
- one pending review item: `Automate release checklist workflow`
- one expensive product task that still needs interpretation, not hype
- an HTML report at `.workledger/agent-cost/reports/summary.html`

Software capex review is still in the repo, but it is a downstream interpretation of the same ledgered work. Start here for the primitive, then go to [Software CapEx Review](software-capex.md) if you want the accounting-facing example.
