from pathlib import Path

from workledger.ingest.loader import ingest_path
from workledger.ingest.normalize import normalize_event
from workledger.models import SourceKind, SpanKind


def test_normalize_openinference_fixture() -> None:
    result = ingest_path(Path("tests/fixtures/openinference_support.jsonl"))
    assert result.ingested == 2
    assert result.spans[0].source_kind == SourceKind.OPENINFERENCE
    assert result.spans[0].span_kind == SpanKind.AGENT
    assert result.spans[0].attributes["ticket_id"] == "CS-999"


def test_normalize_otel_fixture() -> None:
    result = ingest_path(Path("tests/fixtures/otel_marketing.json"))
    assert result.ingested == 1
    assert result.spans[0].source_kind == SourceKind.OPENTELEMETRY
    assert result.spans[0].model_name == "gpt-4.1-mini"


def test_ingest_path_skips_bad_jsonl_lines(tmp_path: Path) -> None:
    fixture = tmp_path / "bad.jsonl"
    fixture.write_text('{"trace_id":"ok","span_id":"a","name":"x","start_time":"2026-04-06T12:00:00+00:00","end_time":"2026-04-06T12:00:01+00:00"}\nnot-json\n', encoding="utf-8")
    result = ingest_path(fixture)
    assert result.ingested == 1
    assert result.skipped == 1
    assert result.errors[0].line == 2


def test_normalize_sdk_event() -> None:
    span = normalize_event(
        {
            "event_type": "observation_span",
            "source_kind": "sdk",
            "trace_id": "trace_1",
            "span_id": "span_1",
            "span_kind": "llm",
            "name": "draft",
            "start_time": "2026-04-06T12:00:00+00:00",
            "end_time": "2026-04-06T12:00:05+00:00",
            "token_input": 10,
            "token_output": 5,
            "token_taxes": [
                {
                    "name": "ca_ai_employer_tax",
                    "jurisdiction": "US-CA",
                    "rate": 0.08,
                    "taxable_tokens": 15,
                    "amount": 0.0008,
                    "currency": "USD",
                }
            ],
            "direct_cost": 0.01,
            "attributes": {},
            "facets": {},
        }
    )
    assert span.source_kind == SourceKind.SDK
    assert span.duration_ms == 5000
    assert span.token_taxes[0].jurisdiction == "US-CA"
    assert span.token_taxes[0].amount == 0.0008


def test_normalize_cloudevent_preserves_provenance() -> None:
    span = normalize_event(
        {
            "specversion": "1.0",
            "id": "evt_1",
            "source": "workledger.test",
            "type": "workledger.observation_span",
            "data": {
                "trace_id": "trace_1",
                "span_id": "span_1",
                "span_kind": "tool",
                "name": "fetch context",
                "start_time": "2026-04-06T12:00:00+00:00",
                "end_time": "2026-04-06T12:00:03+00:00",
                "attributes": {},
                "facets": {},
            },
        }
    )
    assert span.source_kind == SourceKind.CLOUDEVENT
    assert span.span_kind == SpanKind.TOOL


def test_normalize_otel_typed_attributes() -> None:
    span = normalize_event(
        {
            "traceId": "trace_marketing_fixture",
            "spanId": "span_marketing_root",
            "parentSpanId": None,
            "name": "Generate marketing assets",
            "kind": "server",
            "startTime": "2026-04-06T11:00:00+00:00",
            "endTime": "2026-04-06T11:00:09+00:00",
            "status": {"code": "ok"},
            "attributes": [
                {"key": "openinference.span.kind", "value": {"stringValue": "agent"}},
                {"key": "llm.model_name", "value": {"stringValue": "gpt-4.1-mini"}},
                {"key": "llm.cost.usd", "value": {"doubleValue": 0.012}},
                {
                    "key": "labels",
                    "value": {
                        "arrayValue": {
                            "values": [
                                {"stringValue": "marketing"},
                                {"stringValue": "campaign"},
                            ]
                        }
                    },
                },
            ],
        }
    )
    assert span.source_kind == SourceKind.OPENTELEMETRY
    assert span.span_kind == SpanKind.AGENT
    assert span.model_name == "gpt-4.1-mini"
    assert span.direct_cost == 0.012
    assert span.attributes["labels"] == ["marketing", "campaign"]
