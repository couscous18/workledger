# Software Capex Review Sample Dataset

This synthetic dataset is the benchmark/sample input for the public workledger demo.

Each JSONL row contains:

- `case_id`
- `events`
- `expected.work_category`
- `expected.policy_outcome`
- `expected.reviewer_required`

The events are canonical SDK-shaped observation span payloads with software-project metadata, artifact references, and expected capex-review labels.
