from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from workledger.models import ObservationSpan, SourceKind, SpanKind


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=UTC)
    text = str(value).replace("Z", "+00:00")
    return datetime.fromisoformat(text)


def _span_kind(value: Any) -> SpanKind:
    normalized = str(value or "other").lower()
    mapping = {
        "server": SpanKind.ROOT,
        "client": SpanKind.IO,
        "llm": SpanKind.LLM,
        "agent": SpanKind.AGENT,
        "tool": SpanKind.TOOL,
        "retriever": SpanKind.RETRIEVER,
        "evaluator": SpanKind.EVALUATOR,
        "guardrail": SpanKind.GUARDRAIL,
        "review": SpanKind.REVIEW,
        "other": SpanKind.OTHER,
        "root": SpanKind.ROOT,
    }
    return mapping.get(normalized, SpanKind.OTHER)


def _otel_attribute_value(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    for key in (
        "stringValue",
        "boolValue",
        "intValue",
        "doubleValue",
        "bytesValue",
    ):
        if key in value:
            return value[key]
    if "arrayValue" in value:
        values = value["arrayValue"].get("values", [])
        return [_otel_attribute_value(item) for item in values]
    if "kvlistValue" in value:
        values = value["kvlistValue"].get("values", [])
        return {
            str(item["key"]): _otel_attribute_value(item.get("value"))
            for item in values
            if isinstance(item, dict) and item.get("key") is not None
        }
    return value


def normalize_openinference(payload: dict[str, Any]) -> ObservationSpan:
    attributes = dict(payload.get("attributes", {}))
    return ObservationSpan(
        source_kind=SourceKind.OPENINFERENCE,
        trace_id=str(payload["trace_id"]),
        span_id=str(payload["span_id"]),
        parent_span_id=payload.get("parent_span_id"),
        span_kind=_span_kind(payload.get("span_kind")),
        name=payload.get("name", payload.get("operation_name", "openinference-span")),
        start_time=_parse_time(payload["start_time"]),
        end_time=_parse_time(payload["end_time"]),
        model_name=payload.get("model_name"),
        provider=payload.get("provider"),
        tool_name=payload.get("tool_name"),
        token_input=int(payload.get("token_input", payload.get("input_tokens", 0))),
        token_output=int(payload.get("token_output", payload.get("output_tokens", 0))),
        token_taxes=list(payload.get("token_taxes", [])),
        direct_cost=float(payload.get("direct_cost", payload.get("cost", 0.0))),
        status=payload.get("status", "ok"),
        attributes=attributes,
        raw_payload_ref=payload.get("raw_payload_ref"),
        masked=bool(payload.get("masked", False)),
        redaction_applied=bool(payload.get("redaction_applied", False)),
        work_unit_key=payload.get("work_unit_id") or attributes.get("work_unit_key"),
        facets=dict(payload.get("facets", {})),
    )


def normalize_otel(payload: dict[str, Any]) -> ObservationSpan:
    attributes: dict[str, Any] = {
        str(item["key"]): _otel_attribute_value(item.get("value"))
        for item in payload.get("attributes", [])
        if isinstance(item, dict) and item.get("key") is not None
    }
    return ObservationSpan(
        source_kind=SourceKind.OPENTELEMETRY,
        trace_id=str(payload["traceId"]),
        span_id=str(payload["spanId"]),
        parent_span_id=payload.get("parentSpanId"),
        span_kind=_span_kind(attributes.get("openinference.span.kind") or payload.get("kind")),
        name=payload.get("name", "otel-span"),
        start_time=_parse_time(payload.get("startTime") or payload.get("start_time")),
        end_time=_parse_time(payload.get("endTime") or payload.get("end_time")),
        model_name=attributes.get("llm.model_name"),
        provider=attributes.get("llm.provider"),
        tool_name=attributes.get("tool.name"),
        token_input=int(attributes.get("llm.token_count.prompt", 0) or 0),
        token_output=int(attributes.get("llm.token_count.completion", 0) or 0),
        token_taxes=list(payload.get("token_taxes", [])),
        direct_cost=float(attributes.get("llm.cost.usd", 0.0) or 0.0),
        status=payload.get("status", {}).get("code", "ok")
        if isinstance(payload.get("status"), dict)
        else "ok",
        attributes=attributes,
        raw_payload_ref=payload.get("raw_payload_ref"),
        work_unit_key=attributes.get("work_unit_key"),
        facets={},
    )


def normalize_sdk(
    payload: dict[str, Any],
    *,
    source_kind: SourceKind = SourceKind.SDK,
) -> ObservationSpan:
    return ObservationSpan(
        source_kind=source_kind,
        trace_id=str(payload["trace_id"]),
        span_id=str(payload["span_id"]),
        parent_span_id=payload.get("parent_span_id"),
        span_kind=_span_kind(payload.get("span_kind")),
        name=str(payload["name"]),
        start_time=_parse_time(payload["start_time"]),
        end_time=_parse_time(payload["end_time"]),
        model_name=payload.get("model_name"),
        provider=payload.get("provider"),
        tool_name=payload.get("tool_name"),
        token_input=int(payload.get("token_input", 0)),
        token_output=int(payload.get("token_output", 0)),
        token_taxes=list(payload.get("token_taxes", [])),
        direct_cost=float(payload.get("direct_cost", 0.0)),
        status=payload.get("status", "ok"),
        attributes=dict(payload.get("attributes", {})),
        raw_payload_ref=payload.get("raw_payload_ref"),
        masked=bool(payload.get("masked", False)),
        redaction_applied=bool(payload.get("redaction_applied", False)),
        work_unit_key=payload.get("work_unit_key"),
        facets=dict(payload.get("facets", {})),
    )


def normalize_cloudevent(payload: dict[str, Any]) -> ObservationSpan:
    data = dict(payload.get("data", {}))
    if "trace_id" in data:
        return normalize_sdk(data, source_kind=SourceKind.CLOUDEVENT)
    return normalize_openinference(data)


def normalize_event(payload: dict[str, Any]) -> ObservationSpan:
    if payload.get("source_kind") == "sdk" or payload.get("event_type") == "observation_span":
        return normalize_sdk(payload)
    if "traceId" in payload and "spanId" in payload:
        return normalize_otel(payload)
    if payload.get("specversion") and payload.get("data"):
        return normalize_cloudevent(payload)
    if "trace_id" in payload and "span_id" in payload:
        return normalize_openinference(payload)
    raise ValueError(f"unsupported event payload shape: keys={sorted(payload.keys())}")
