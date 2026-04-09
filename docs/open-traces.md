# Open Traces

Open-source AI is producing more public traces.

That matters because traces are now becoming shareable artifacts and proof surfaces:

- agent messages
- trajectories
- span trees
- token and cost totals

What is still missing is an open way to turn those traces into accountable work.

`workledger` fills that gap by normalizing traces into `ObservationSpan`s and rolling them into `WorkUnit`s with evidence, lineage, review states, and work-attached cost.

## Why Public Traces Matter

Public traces make the trace-to-work problem inspectable in the open.

They let builders see, end to end:

- what the source trace looked like
- how that trace was normalized
- how multiple steps were grouped into understandable work
- where ambiguity stayed visible instead of being hidden

That makes public traces the best entrypoint for the repo.
They are the proof path, not the whole product story.

## Supported Public Dataset Shapes

| dataset | url | shape | support | demo |
| --- | --- | --- | --- | --- |
| smolagents/gaia-traces | https://huggingface.co/datasets/smolagents/gaia-traces | messages / trajectories | supported | yes |
| kshitijthakkar/smoltrace-traces-20260130_053009 | https://huggingface.co/datasets/kshitijthakkar/smoltrace-traces-20260130_053009 | trace + spans | supported | yes |
| smolagents/codeagent-traces | https://huggingface.co/datasets/smolagents/codeagent-traces | messages / outcomes | planned | no |

## Why Traces Alone Are Not Enough

Traces preserve execution detail.
They do not, by themselves, tell you:

- which steps belong to one understandable unit of work
- where ambiguity should stay visible
- how evidence should stay attached to interpretation
- how cost should be attributed to the work, not just the underlying calls

## What `workledger` Adds After Ingestion

`workledger` does not stop at showing the trace.
It adds the ledger layer on top of the trace:

- `ObservationSpan` as the normalized execution record
- `WorkUnit` as the durable unit of work people can inspect
- evidence bundles and lineage refs for reviewability
- direct cost, allocated cost, and total cost attached to rolled work
- review, policy, and economics as downstream interpretations

## How `workledger` Fits

`workledger` is not a tracing backend.
It is the attribution layer between public traces and legible work.

That makes it useful to:

- agent builders
- telemetry builders
- Hugging Face dataset users
- teams trying to make agent work reviewable

## Adding More Adapters

New public trace formats should:

- map into `ObservationSpan`
- preserve stable source refs in `raw_payload_ref`
- store source-specific metadata in namespaced facets
- include a small fixture and a demo-sized path
