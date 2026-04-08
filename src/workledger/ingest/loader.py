from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from workledger.ingest.normalize import normalize_event
from workledger.models import IngestError, IngestResult, ObservationSpan


def _load_json_file(path: Path) -> tuple[list[dict[str, Any]], list[IngestError]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [dict(item) for item in payload], []
    if isinstance(payload, dict) and "events" in payload:
        return [dict(item) for item in payload["events"]], []
    if isinstance(payload, dict):
        return [payload], []
    raise ValueError(f"unsupported json payload in {path}")


def _load_jsonl_file(path: Path) -> tuple[list[dict[str, Any]], list[IngestError]]:
    events: list[dict[str, Any]] = []
    errors: list[IngestError] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            errors.append(IngestError(line=index, error=f"invalid json: {exc.msg}"))
            continue
        if not isinstance(payload, dict):
            errors.append(IngestError(line=index, error="expected a JSON object"))
            continue
        events.append(payload)
    return events, errors


def load_events(path: Path) -> tuple[list[dict[str, Any]], list[IngestError]]:
    if path.suffix == ".jsonl":
        return _load_jsonl_file(path)
    if path.suffix == ".json":
        return _load_json_file(path)
    raise ValueError(f"unsupported input file: {path}")


def normalize_events(events: Iterable[dict[str, Any]]) -> IngestResult:
    spans: list[ObservationSpan] = []
    errors: list[IngestError] = []
    for index, event in enumerate(events, start=1):
        try:
            spans.append(normalize_event(event))
        except (TypeError, ValueError, KeyError) as exc:
            errors.append(IngestError(line=index, error=str(exc)))
    return IngestResult(
        ingested=len(spans),
        skipped=len(errors),
        errors=errors,
        spans=spans,
    )


def ingest_path(path: Path) -> IngestResult:
    events, load_errors = load_events(path)
    result = normalize_events(events)
    result.errors = [*load_errors, *result.errors]
    result.skipped = len(result.errors)
    return result
