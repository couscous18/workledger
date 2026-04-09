from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from workledger.models import IngestResult, ObservationSpan, SourceKind, SpanKind

try:
    from datasets import load_dataset
except ImportError as exc:  # pragma: no cover - import guard
    load_dataset = None
    _DATASETS_IMPORT_ERROR: ImportError | None = exc
else:  # pragma: no cover - alias only
    _DATASETS_IMPORT_ERROR = None


def _require_datasets() -> Any:
    if load_dataset is None:
        raise RuntimeError(
            "The `datasets` package is required for `wl ingest-hf` and public trace demos."
        ) from _DATASETS_IMPORT_ERROR
    return load_dataset


def _stable_timestamp(row_index: int, offset_seconds: int = 0) -> datetime:
    base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return base + timedelta(minutes=row_index, seconds=offset_seconds)


def _slugify_dataset_id(dataset_id: str) -> str:
    return dataset_id.replace("/", "-").replace(":", "-")


def _raw_ref(dataset_id: str, split: str, row_index: int, suffix: str) -> str:
    return f"hf://{dataset_id}/{split}/{row_index}#{suffix}"


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content") or item.get("value")
                if text:
                    parts.append(str(text).strip())
        return "\n".join(part for part in parts if part)
    if isinstance(content, dict):
        text = content.get("text") or content.get("content") or content.get("value")
        return str(text).strip() if text else json.dumps(content, sort_keys=True)
    return str(content).strip()


def _truncate(text: str, limit: int = 240) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _span_kind_from_role(role: str) -> SpanKind:
    normalized = role.lower()
    if normalized == "assistant":
        return SpanKind.LLM
    if normalized in {"tool", "function"}:
        return SpanKind.TOOL
    if normalized == "system":
        return SpanKind.GUARDRAIL
    if normalized == "user":
        return SpanKind.IO
    return SpanKind.OTHER


def _string_value(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _number_value(payload: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _int_value(payload: dict[str, Any], *keys: str) -> int:
    value = _number_value(payload, *keys)
    return int(value or 0)


class PublicTraceAdapter(Protocol):
    name: str

    def supports(self, dataset_id: str, row: dict[str, Any]) -> bool: ...

    def adapt(
        self,
        *,
        dataset_id: str,
        split: str,
        row_index: int,
        row: dict[str, Any],
    ) -> list[ObservationSpan]: ...


@dataclass(slots=True)
class HuggingFaceDatasetBundle:
    dataset_id: str
    split: str
    adapter_name: str
    rows: list[dict[str, Any]]
    spans: list[ObservationSpan]


@dataclass(slots=True)
class HuggingFaceIngestResult:
    dataset_id: str
    split: str
    adapter_name: str
    row_count: int
    raw_path: Path
    ingest: IngestResult


class GaiaTraceAdapter:
    name = "gaia"

    def supports(self, dataset_id: str, row: dict[str, Any]) -> bool:
        lowered = dataset_id.lower()
        return "gaia-traces" in lowered or "messages" in row

    def adapt(
        self,
        *,
        dataset_id: str,
        split: str,
        row_index: int,
        row: dict[str, Any],
    ) -> list[ObservationSpan]:
        messages = row.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValueError("GAIA adapter expected a non-empty `messages` list")

        trace_id = str(row.get("trace_id") or row.get("id") or f"{_slugify_dataset_id(dataset_id)}-{row_index}")
        work_unit_key = f"hf:{dataset_id}:{split}:{row_index}"
        base_time = _stable_timestamp(row_index)
        user_messages = [
            _message_text(message.get("content"))
            for message in messages
            if isinstance(message, dict) and str(message.get("role", "")).lower() == "user"
        ]
        assistant_messages = [
            _message_text(message.get("content"))
            for message in messages
            if isinstance(message, dict) and str(message.get("role", "")).lower() == "assistant"
        ]
        system_prompt = _string_value(row, "system_prompt", "prompt")
        title = (
            _string_value(row, "task", "question", "instruction", "problem")
            or next((message for message in user_messages if message), "GAIA public trace")
        )
        final_answer = (
            _string_value(row, "final_answer", "prediction", "answer")
            or next((message for message in reversed(assistant_messages) if message), None)
        )
        ambiguous = final_answer is None or any(not message for message in assistant_messages)
        spans: list[ObservationSpan] = [
            ObservationSpan(
                source_kind=SourceKind.HUGGINGFACE,
                trace_id=trace_id,
                span_id=f"{trace_id}:root",
                span_kind=SpanKind.AGENT,
                name=title,
                start_time=base_time,
                end_time=base_time + timedelta(seconds=max(1, len(messages))),
                token_input=_int_value(row, "prompt_tokens", "input_tokens"),
                token_output=_int_value(row, "completion_tokens", "output_tokens"),
                direct_cost=_number_value(row, "cost", "total_cost") or 0.0,
                model_name=_string_value(row, "model_id", "model", "model_name"),
                provider=_string_value(row, "provider"),
                status="review_required" if ambiguous else "ok",
                work_unit_key=work_unit_key,
                raw_payload_ref=_raw_ref(dataset_id, split, row_index, "row"),
                attributes={
                    "task_title": _truncate(title, 160),
                    "objective": _truncate(title, 240),
                    "review_required": ambiguous,
                    "labels": ["open-traces", "huggingface", "gaia"],
                    "dataset_id": dataset_id,
                    "dataset_split": split,
                    "dataset_row_index": row_index,
                    "system_prompt": system_prompt,
                    "final_answer": final_answer,
                    "output_artifacts": [f"hf://{dataset_id}/{split}/{row_index}#final-answer"]
                    if final_answer
                    else [],
                },
                facets={
                    "hf": {
                        "dataset_id": dataset_id,
                        "split": split,
                        "adapter": self.name,
                        "row_index": row_index,
                        "shape": "messages",
                        "synthetic_timestamps": True,
                    },
                    "trace_to_work": {
                        "trace_shape": "messages",
                        "ambiguity_reason": "missing_final_answer" if ambiguous else None,
                        "system_prompt": system_prompt,
                    },
                },
            )
        ]

        for message_index, message in enumerate(messages, start=1):
            if not isinstance(message, dict):
                continue
            role = str(message.get("role", "other"))
            content = _message_text(message.get("content"))
            timestamp = _stable_timestamp(row_index, message_index)
            spans.append(
                ObservationSpan(
                    source_kind=SourceKind.HUGGINGFACE,
                    trace_id=trace_id,
                    span_id=f"{trace_id}:msg:{message_index}",
                    parent_span_id=f"{trace_id}:root",
                    span_kind=_span_kind_from_role(role),
                    name=f"{role}: {_truncate(content or 'message', 80)}",
                    start_time=timestamp,
                    end_time=timestamp + timedelta(seconds=1),
                    model_name=_string_value(message, "model", "model_id") or _string_value(
                        row, "model_id", "model", "model_name"
                    ),
                    provider=_string_value(row, "provider"),
                    direct_cost=0.0,
                    status="review_required" if ambiguous else "ok",
                    work_unit_key=work_unit_key,
                    raw_payload_ref=_raw_ref(dataset_id, split, row_index, f"message-{message_index}"),
                    attributes={
                        "role": role,
                        "content_preview": _truncate(content, 240),
                        "review_required": ambiguous and role == "assistant",
                        "labels": ["open-traces", "huggingface", role.lower()],
                    },
                    facets={
                        "hf": {
                            "dataset_id": dataset_id,
                            "split": split,
                            "adapter": self.name,
                            "row_index": row_index,
                            "message_index": message_index,
                        }
                    },
                )
            )
        return spans


class SmoltraceAdapter:
    name = "smoltrace"

    def supports(self, dataset_id: str, row: dict[str, Any]) -> bool:
        lowered = dataset_id.lower()
        return "smoltrace" in lowered or ("trace_id" in row and "spans" in row)

    def adapt(
        self,
        *,
        dataset_id: str,
        split: str,
        row_index: int,
        row: dict[str, Any],
    ) -> list[ObservationSpan]:
        trace_id = str(row.get("trace_id") or row.get("id") or f"smoltrace-{row_index}")
        spans_payload = row.get("spans")
        if isinstance(spans_payload, list):
            payloads = [item for item in spans_payload if isinstance(item, dict)]
        else:
            payloads = [row]
        if not payloads:
            raise ValueError("smoltrace adapter expected `spans` data or span-like rows")

        row_start = _stable_timestamp(row_index)
        root_ref = _raw_ref(dataset_id, split, row_index, "trace")
        root_cost = _number_value(row, "cost", "total_cost", "cost_usd") or 0.0
        root_duration_ms = max(
            1,
            int(_number_value(row, "duration_ms", "duration", "total_duration_ms") or 0.0),
        )
        adapted: list[ObservationSpan] = []
        for span_index, payload in enumerate(payloads, start=1):
            start_time = self._start_time(payload, row_start, span_index)
            duration_ms = max(
                1,
                int(_number_value(payload, "duration_ms", "duration", "latency_ms") or 1000),
            )
            end_time = self._end_time(payload, start_time, duration_ms)
            span_id = str(payload.get("span_id") or payload.get("id") or f"{trace_id}:span:{span_index}")
            parent_span_id = payload.get("parent_span_id") or payload.get("parent_id")
            span_kind = self._span_kind(payload)
            name = _string_value(payload, "name", "operation", "span_name") or span_kind.value
            token_input = _int_value(
                payload,
                "token_input",
                "input_tokens",
                "prompt_tokens",
            )
            token_output = _int_value(
                payload,
                "token_output",
                "output_tokens",
                "completion_tokens",
            )
            direct_cost = _number_value(payload, "cost", "direct_cost", "cost_usd") or 0.0
            if span_index == 1 and direct_cost == 0.0 and root_cost > 0.0:
                direct_cost = root_cost
            adapted.append(
                ObservationSpan(
                    source_kind=SourceKind.HUGGINGFACE,
                    trace_id=trace_id,
                    span_id=span_id,
                    parent_span_id=str(parent_span_id) if parent_span_id else None,
                    span_kind=span_kind,
                    name=name,
                    start_time=start_time,
                    end_time=end_time,
                    model_name=_string_value(payload, "model", "model_id", "model_name")
                    or _string_value(row, "model", "model_id", "model_name"),
                    provider=_string_value(payload, "provider") or _string_value(row, "provider"),
                    tool_name=_string_value(payload, "tool_name", "tool"),
                    token_input=token_input,
                    token_output=token_output,
                    direct_cost=direct_cost,
                    status=str(payload.get("status") or row.get("status") or "ok"),
                    raw_payload_ref=_raw_ref(dataset_id, split, row_index, f"span-{span_index}"),
                    work_unit_key=None,
                    attributes={
                        "labels": ["open-traces", "huggingface", "smoltrace"],
                        "trace_id": trace_id,
                        "dataset_id": dataset_id,
                        "dataset_split": split,
                        "review_required": span_index == 1 and len(payloads) > 4,
                        "span_events": payload.get("events", []),
                    },
                    facets={
                        "hf": {
                            "dataset_id": dataset_id,
                            "split": split,
                            "adapter": self.name,
                            "row_index": row_index,
                            "shape": "trace+spans",
                        },
                        "smoltrace": {
                            "trace_id": trace_id,
                            "row_ref": root_ref,
                            "row_duration_ms": root_duration_ms,
                            "row_cost": root_cost,
                            "total_input_tokens": _int_value(
                                row, "input_tokens", "prompt_tokens", "total_input_tokens"
                            ),
                            "total_output_tokens": _int_value(
                                row,
                                "output_tokens",
                                "completion_tokens",
                                "total_output_tokens",
                            ),
                            "span_index": span_index,
                        },
                    },
                )
            )
        return adapted

    def _span_kind(self, payload: dict[str, Any]) -> SpanKind:
        raw_kind = str(payload.get("kind") or payload.get("type") or "other").lower()
        if raw_kind in {"root", "trace"}:
            return SpanKind.ROOT
        if raw_kind in {"llm", "assistant"}:
            return SpanKind.LLM
        if raw_kind in {"agent", "workflow"}:
            return SpanKind.AGENT
        if raw_kind in {"tool", "function"}:
            return SpanKind.TOOL
        if raw_kind in {"retriever", "retrieve"}:
            return SpanKind.RETRIEVER
        if raw_kind in {"guardrail"}:
            return SpanKind.GUARDRAIL
        if raw_kind in {"review", "human_review"}:
            return SpanKind.REVIEW
        if raw_kind in {"io", "client"}:
            return SpanKind.IO
        return SpanKind.OTHER

    def _start_time(
        self, payload: dict[str, Any], row_start: datetime, span_index: int
    ) -> datetime:
        value = payload.get("start_time") or payload.get("start") or payload.get("started_at")
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return row_start + timedelta(seconds=span_index - 1)

    def _end_time(
        self,
        payload: dict[str, Any],
        start_time: datetime,
        duration_ms: int,
    ) -> datetime:
        value = payload.get("end_time") or payload.get("end") or payload.get("ended_at")
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return start_time + timedelta(milliseconds=duration_ms)


ADAPTERS: tuple[PublicTraceAdapter, ...] = (GaiaTraceAdapter(), SmoltraceAdapter())


def _resolve_adapter(
    adapter_name: str,
    dataset_id: str,
    rows: list[dict[str, Any]],
) -> PublicTraceAdapter:
    if adapter_name != "auto":
        for adapter in ADAPTERS:
            if adapter.name == adapter_name:
                return adapter
        raise ValueError(f"unknown Hugging Face adapter: {adapter_name}")
    sample = rows[0] if rows else {}
    for adapter in ADAPTERS:
        if adapter.supports(dataset_id, sample):
            return adapter
    raise ValueError(f"could not infer an adapter for {dataset_id}")


def _sample_rows(dataset_id: str, split: str, limit: int | None, seed: int) -> list[dict[str, Any]]:
    loader = _require_datasets()
    dataset = loader(dataset_id, split=split)
    if hasattr(dataset, "shuffle"):
        dataset = dataset.shuffle(seed=seed)
    row_count = len(dataset)
    selected_count = row_count if limit is None else min(limit, row_count)
    if hasattr(dataset, "select"):
        dataset = dataset.select(range(selected_count))
    return [dict(dataset[index]) for index in range(selected_count)]


def adapt_huggingface_dataset(
    *,
    dataset_id: str,
    split: str,
    adapter_name: str = "auto",
    limit: int | None = None,
    seed: int = 7,
) -> HuggingFaceDatasetBundle:
    rows = _sample_rows(dataset_id, split, limit, seed)
    adapter = _resolve_adapter(adapter_name, dataset_id, rows)
    spans: list[ObservationSpan] = []
    for row_index, row in enumerate(rows):
        spans.extend(
            adapter.adapt(
                dataset_id=dataset_id,
                split=split,
                row_index=row_index,
                row=row,
            )
        )
    return HuggingFaceDatasetBundle(
        dataset_id=dataset_id,
        split=split,
        adapter_name=adapter.name,
        rows=rows,
        spans=spans,
    )


def write_huggingface_rows(bundle: HuggingFaceDatasetBundle, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(row, sort_keys=True, default=str) for row in bundle.rows)
    destination.write_text(payload + ("\n" if payload else ""), encoding="utf-8")
    return destination
