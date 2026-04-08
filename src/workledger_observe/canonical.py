from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from workledger.models import SpanKind
from workledger.utils.ids import new_id


def git_metadata(
    repository: str,
    *,
    branch: str | None = None,
    commit_sha: str | None = None,
    issue_labels: list[str] | None = None,
    files_touched: list[str] | None = None,
    deployment_target: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"repository": repository}
    if branch is not None:
        payload["branch"] = branch
    if commit_sha is not None:
        payload["commit_sha"] = commit_sha
    if issue_labels is not None:
        payload["issue_labels"] = issue_labels
    if files_touched is not None:
        payload["files_touched"] = files_touched
    if deployment_target is not None:
        payload["deployment_target"] = deployment_target
    if extra:
        payload.update(extra)
    return payload


def project_metadata(
    project: str,
    *,
    team: str | None = None,
    cost_center: str | None = None,
    owner: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"project": project}
    if team is not None:
        payload["team"] = team
    if cost_center is not None:
        payload["cost_center"] = cost_center
    if owner is not None:
        payload["owner"] = owner
    if extra:
        payload.update(extra)
    return payload


def artifact_ref(
    uri: str,
    *,
    kind: str = "output",
    title: str | None = None,
    digest: str | None = None,
    source_system: str = "trace",
    sensitivity: str = "internal",
    preview: str | None = None,
    timestamp: datetime | None = None,
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "artifact_id": new_id("art"),
        "kind": kind,
        "uri": uri,
        "source_system": source_system,
        "sensitivity": sensitivity,
        "timestamp": (timestamp or datetime.now(UTC)).isoformat(),
    }
    if title is not None:
        payload["title"] = title
    if digest is not None:
        payload["digest"] = digest
    if preview is not None:
        payload["preview"] = preview
    if attributes is not None:
        payload["attributes"] = attributes
    return payload


def build_observation_span_event(
    *,
    trace_id: str,
    span_id: str | None = None,
    name: str,
    span_kind: SpanKind | str,
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
    status: str = "ok",
    attributes: dict[str, Any] | None = None,
    facets: dict[str, Any] | None = None,
    source_kind: str = "sdk",
    occurred_at: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event_type": "observation_span",
        "source_kind": source_kind,
        "trace_id": trace_id,
        "span_id": span_id or new_id("span"),
        "parent_span_id": parent_span_id,
        "span_kind": str(span_kind),
        "name": name,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "model_name": model_name,
        "provider": provider,
        "tool_name": tool_name,
        "token_input": token_input,
        "token_output": token_output,
        "token_taxes": token_taxes or [],
        "direct_cost": direct_cost,
        "status": status,
        "attributes": attributes or {},
        "facets": facets or {},
    }
    if occurred_at is not None:
        payload["occurred_at"] = occurred_at
    return payload
