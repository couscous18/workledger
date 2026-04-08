from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workledger.models import SpanKind
from workledger.utils.ids import new_id
from workledger_observe.canonical import build_observation_span_event


class TraceRecorder:
    """Small local recorder for emitting SDK-friendly JSONL spans."""

    def __init__(self, destination: Path, trace_id: str | None = None) -> None:
        self.destination = destination
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        self.trace_id = trace_id or new_id("trace")

    def emit(
        self,
        *,
        span_id: str | None = None,
        name: str,
        span_kind: SpanKind,
        start_time: datetime,
        end_time: datetime,
        parent_span_id: str | None = None,
        model_name: str | None = None,
        provider: str | None = None,
        tool_name: str | None = None,
        token_input: int = 0,
        token_output: int = 0,
        token_taxes: list[dict[str, Any]] | None = None,
        direct_cost: float = 0.0,
        attributes: dict[str, Any] | None = None,
        facets: dict[str, Any] | None = None,
    ) -> str:
        span_id = span_id or new_id("span")
        payload = build_observation_span_event(
            trace_id=self.trace_id,
            span_id=span_id,
            name=name,
            span_kind=span_kind,
            start_time=start_time,
            end_time=end_time,
            parent_span_id=parent_span_id,
            model_name=model_name,
            provider=provider,
            tool_name=tool_name,
            token_input=token_input,
            token_output=token_output,
            token_taxes=token_taxes,
            direct_cost=direct_cost,
            attributes=attributes,
            facets=facets,
        )
        with self.destination.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
        return span_id


@contextmanager
def observe_span(
    recorder: TraceRecorder,
    *,
    name: str,
    span_kind: SpanKind,
    parent_span_id: str | None = None,
    model_name: str | None = None,
    provider: str | None = None,
    tool_name: str | None = None,
    token_input: int = 0,
    token_output: int = 0,
    token_taxes: list[dict[str, Any]] | None = None,
    direct_cost: float = 0.0,
    attributes: dict[str, Any] | None = None,
    facets: dict[str, Any] | None = None,
) -> Iterator[str]:
    start = datetime.now(UTC)
    span_id = new_id("span")
    try:
        yield span_id
    finally:
        end = datetime.now(UTC)
        recorder.emit(
            span_id=span_id,
            name=name,
            span_kind=span_kind,
            start_time=start,
            end_time=end,
            parent_span_id=parent_span_id,
            model_name=model_name,
            provider=provider,
            tool_name=tool_name,
            token_input=token_input,
            token_output=token_output,
            token_taxes=token_taxes,
            direct_cost=direct_cost,
            attributes=attributes,
            facets=facets,
        )
