# Adapters & Integrations

Adapters and normalizers convert source payloads into `ObservationSpan`.

## Local Input Shapes Supported By `wl ingest`

`wl ingest` accepts `.json` and `.jsonl`. The normalizer currently detects these payload families:

- canonical SDK-shaped observation events
- OpenInference-like payloads
- OTEL-style JSON spans
- CloudEvents whose `data` contains canonical SDK or OpenInference-like payloads

## Hugging Face Adapters Implemented Today

- `gaia`
  - targets message-style rows such as `smolagents/gaia-traces`
  - emits one root agent span plus per-message spans
  - sets `work_unit_key` so one dataset row rolls into one candidate work unit
- `smoltrace`
  - targets trace-and-span rows such as `kshitijthakkar/smoltrace-traces-20260130_053009`
  - preserves span hierarchy, duration, cost, and row lineage
  - stores dataset metadata under `facets["hf"]` and `facets["smoltrace"]`

## Adapter Design

The adapter seam in code is intentionally small:

- choose or infer the source shape
- map source rows into one or more `ObservationSpan`
- preserve lineage in `raw_payload_ref`
- attach source-specific metadata in namespaced `facets`
- optionally set `work_unit_key` when the source already exposes a good rollup boundary

## Hugging Face Lineage

Public dataset rows are preserved with refs like:

```text
hf://smolagents/gaia-traces/train/0#message-2
hf://kshitijthakkar/smoltrace-traces-20260130_053009/train/1#span-3
```

Those refs then stay attached to evidence and `WorkUnit.lineage_refs`.

## Extension Points That Actually Exist

- add a new payload family in `src/workledger/ingest/normalize.py`
- add a new Hugging Face adapter in `src/workledger/adapters/huggingface.py`
- extend examples and tests with new fixtures and a runnable demo-sized sample

There is no plugin registry in the current codebase; adapters are code-level extensions.
