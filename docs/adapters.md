# Adapters & Integrations

Adapters normalize source traces into `ObservationSpan`.

Current built-ins:

- `gaia`
  maps message / trajectory rows such as `smolagents/gaia-traces`
- `smoltrace`
  maps trace / span rows such as `kshitijthakkar/smoltrace-traces-20260130_053009`
- existing JSON and JSONL normalization for OpenTelemetry-like, OpenInference-like, CloudEvents, and SDK-shaped traces

## Adapter Design

The adapter seam is intentionally small:

- detect or choose a source shape
- map source rows into `ObservationSpan`
- preserve lineage in `raw_payload_ref`
- attach dataset-specific metadata in namespaced `facets`

## Hugging Face Lineage

Public dataset rows are preserved with refs like:

```text
hf://smolagents/gaia-traces/train/0#message-2
hf://kshitijthakkar/smoltrace-traces-20260130_053009/train/1#span-3
```

Those refs then stay attached to evidence and `WorkUnit.lineage_refs`.
