# Adapters & Integrations

V1 supports normalization from:

- OpenTelemetry-like span JSON
- OpenInference-like span JSON
- CloudEvents JSON
- raw JSONL batches
- SDK-emitted canonical span payloads

Adapters normalize into `ObservationSpan` before rollup and policy evaluation.

## JSONL

Each line should be a single event object. Malformed lines are skipped and reported during ingest instead of crashing the full batch.

## OpenInference-Like

Provide `trace_id`, `span_id`, `start_time`, `end_time`, and optional token and cost fields.

## OpenTelemetry-Like

Provide `traceId`, `spanId`, timing fields, and attributes such as `llm.model_name`, `llm.token_count.prompt`, and `llm.cost.usd`.

## SDK Events

If you control the instrumentation code, canonical SDK-shaped events are the simplest path because they map directly into WorkLedger’s normalized schema.
