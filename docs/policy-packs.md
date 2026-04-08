# Policy Packs

Policy packs are YAML files that sit on top of the ledgered work layer. They define:

- a policy basis
- defaults
- prioritized rules
- rule explanations
- candidate treatment
- review flags

Rules evaluate extracted `WorkUnit` features, not raw telemetry volume alone.

The flagship public story for the repo is the agent work ledger. Software capex review is a downstream example of what becomes possible once work has been rolled up into `WorkUnit`s with evidence and review state.
