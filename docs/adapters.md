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

## Trace Contract

The normalized object is `ObservationSpan`. Keep raw provider payloads outside the ledger when possible and store a pointer in `raw_payload_ref`.

| WorkLedger field | Required | OpenTelemetry / OpenInference source | Notes |
| --- | --- | --- | --- |
| `trace_id` | yes | `traceId` or `trace_id` | Stable run or request trace identifier. |
| `span_id` | yes | `spanId` or `span_id` | Stable source span identifier. |
| `parent_span_id` | no | `parentSpanId` or `parent_span_id` | Preserves execution hierarchy. |
| `span_kind` | no | `openinference.span.kind`, `kind`, or `span_kind` | Use `agent`, `llm`, `tool`, `retriever`, `review`, or `other`. |
| `name` | yes | span `name` or `operation_name` | Human-readable action label. |
| `start_time`, `end_time` | yes | OTEL timestamps or ISO datetimes | Used for ordering, duration, and rollup. |
| `model_name` | no | `llm.model_name` or `model_name` | Prefer provider model ID when known. |
| `provider` | no | `llm.provider` or `provider` | Example: `openai`, `anthropic`, `local`. |
| `tool_name` | no | `tool.name` or `tool_name` | Use for tool spans. |
| `token_input`, `token_output` | no | `llm.token_count.prompt`, `llm.token_count.completion` | Defaults to `0` when absent. |
| `direct_cost` | no | `llm.cost.usd` or `cost` | Observed cost only; modeled costs belong in reports. |
| `work_unit_key` | no | `work_unit_key`, `task_id`, `issue_id`, `ticket_id`, `campaign_id`, `session_id` | Best hint for grouping spans into work units. |
| `masked`, `redaction_applied` | no | canonical SDK fields | Set these when prompts, outputs, or attributes were privacy-filtered before ingest. |
| `attributes` | no | source attributes | Keep source metadata here; do not rely on unknown keys for public semantics. |
| `facets` | no | canonical SDK field | Namespaced, domain-specific metadata that downstream policy packs may understand. |

## Facet Namespaces

Facets are intentionally open, but shared names make community adapters easier to compare. Unknown facets are treated as opaque and should be preserved by consumers.

| Namespace | Common fields | Use |
| --- | --- | --- |
| `git` | `repository`, `branch`, `commit`, `pull_request`, `issue_id`, `issue_labels` | Connect agent work to source-control context. |
| `llm` | `prompt_version`, `temperature`, `model_family`, `deployment` | Record model invocation context that is not already canonical. |
| `agent` | `name`, `version`, `run_id`, `workflow` | Attribute work to an agent or workflow. |
| `tool` | `name`, `version`, `input_artifact`, `output_artifact` | Describe tool-mediated work and artifacts. |
| `review` | `reviewer`, `review_state`, `approval_ref` | Attach human review or approval context. |
| `privacy` | `redaction_policy`, `masked_fields`, `retention_class` | Explain what was removed or masked before sharing. |
| `source` | `system`, `license`, `dataset`, `uri` | Attribute source data, examples, or benchmark traces. |

Example:

```json
{
  "trace_id": "trace_123",
  "span_id": "span_456",
  "span_kind": "agent",
  "name": "Patch timeout regression",
  "start_time": "2026-04-06T12:00:00+00:00",
  "end_time": "2026-04-06T12:00:05+00:00",
  "work_unit_key": "issue-142",
  "masked": true,
  "redaction_applied": true,
  "facets": {
    "git": {
      "repository": "product-api",
      "branch": "fix/issue-142-timeouts",
      "commit": "abc1234"
    },
    "agent": {
      "name": "release-helper",
      "workflow": "bugfix"
    },
    "privacy": {
      "redaction_policy": "internal-v1",
      "masked_fields": ["prompt", "tool.input"]
    },
    "source": {
      "system": "github",
      "uri": "https://github.com/example/product-api/issues/142"
    }
  }
}
```
