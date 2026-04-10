# Open Traces

Public traces are one supported input family in `workledger`, not the whole repository story.

They matter here because they are easy-to-share test cases for the normalize-and-rollup pipeline:

- agent messages
- trajectories
- span trees
- token and cost totals

The implemented contribution is still the same:

- normalize source records into `ObservationSpan`
- roll them into `WorkUnit`
- optionally classify and report on those work units

## Supported Public Dataset Shapes

| dataset | url | shape | support | demo |
| --- | --- | --- | --- | --- |
| smolagents/gaia-traces | https://huggingface.co/datasets/smolagents/gaia-traces | messages / trajectories | supported | yes |
| kshitijthakkar/smoltrace-traces-20260130_053009 | https://huggingface.co/datasets/kshitijthakkar/smoltrace-traces-20260130_053009 | trace + spans | supported | yes |
| smolagents/codeagent-traces | https://huggingface.co/datasets/smolagents/codeagent-traces | messages / outcomes | planned | no |

## What The Current Adapters Actually Do

- `gaia` maps a message-style row into one root span plus per-message spans
- `smoltrace` maps trace-and-span rows into span-preserving `ObservationSpan`
- both preserve Hugging Face lineage in `raw_payload_ref`
- both populate dataset metadata in `facets["hf"]`

## What `workledger` Adds After Ingestion

- `ObservationSpan` as the normalized execution record
- `WorkUnit` as the rolled unit of work people can inspect
- evidence bundles and lineage refs
- direct and allocated cost attached to rolled work
- optional review, policy, and economics layers after rollup

## How `workledger` Fits

`workledger` is not a trace viewer or tracing backend. In this repo, public traces are just one way to feed the same local pipeline.

## Adding More Adapters

New public trace formats should:

- map into `ObservationSpan`
- preserve stable source refs in `raw_payload_ref`
- store source-specific metadata in namespaced facets
- include a small fixture and a demo-sized path
