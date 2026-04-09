# Open Traces

Open-source AI is producing more public traces.

That matters because traces are now becoming shareable artifacts:

- agent messages
- trajectories
- span trees
- token and cost totals

What is still missing is an open way to attribute those traces to work.

`workledger` fills that gap by turning traces into `WorkUnit`s with evidence, lineage, and review states.

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
