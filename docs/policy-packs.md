# Policy Packs

Policy packs are YAML files that sit on top of the ledgered work layer. They define:

- a policy basis
- defaults
- prioritized rules
- rule explanations
- candidate treatment
- review flags

Rules evaluate extracted `WorkUnit` features, not raw telemetry volume alone.

In the current repository, policy packs are a downstream layer. Software capex review is an example of what can be built on top of rolled `WorkUnit`s with evidence and review state.
