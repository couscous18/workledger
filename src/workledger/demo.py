"""Synthetic trace generators for coding, marketing, and support scenarios."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from workledger import WorkledgerConfig, WorkledgerPipeline
from workledger.models import SpanKind
from workledger.utils.ids import new_id

HF_DEMOS: dict[str, dict[str, Any]] = {
    "hf-gaia": {
        "dataset_id": "smolagents/gaia-traces",
        "adapter": "gaia",
        "split": "train",
        "limit": 3,
        "seed": 7,
        "include_economics": False,
    },
    "hf-smoltrace": {
        "dataset_id": "kshitijthakkar/smoltrace-traces-20260130_053009",
        "adapter": "smoltrace",
        "split": "train",
        "limit": 3,
        "seed": 7,
        "include_economics": False,
    },
}


def _event(
    *,
    trace_id: str,
    span_id: str,
    parent_span_id: str | None,
    span_kind: SpanKind,
    name: str,
    start: datetime,
    duration_ms: int,
    direct_cost: float,
    token_input: int = 0,
    token_output: int = 0,
    attributes: dict[str, Any] | None = None,
    facets: dict[str, Any] | None = None,
    tool_name: str | None = None,
    model_name: str | None = None,
) -> dict[str, Any]:
    return {
        "event_type": "observation_span",
        "source_kind": "sdk",
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "span_kind": span_kind,
        "name": name,
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(milliseconds=duration_ms)).isoformat(),
        "direct_cost": direct_cost,
        "token_input": token_input,
        "token_output": token_output,
        "tool_name": tool_name,
        "model_name": model_name,
        "provider": "openai",
        "attributes": attributes or {},
        "facets": facets or {},
        "status": "ok",
    }


def coding_demo_events() -> list[dict[str, Any]]:
    base = datetime(2026, 4, 6, 12, 0, tzinfo=UTC)
    trace_maintenance = new_id("trace")
    trace_feature = new_id("trace")
    trace_internal = new_id("trace")
    return [
        _event(
            trace_id=trace_maintenance,
            span_id="span_root_bug",
            parent_span_id=None,
            span_kind=SpanKind.AGENT,
            name="Resolve incident ticket BUG-142",
            start=base,
            duration_ms=22_000,
            direct_cost=0.018,
            token_input=980,
            token_output=620,
            model_name="gpt-4.1-mini",
            attributes={
                "issue_id": "BUG-142",
                "task_title": "Patch customer API timeout regression",
                "objective": "Ship minimal-risk production fix for API timeout regression",
                "project": "product-api",
                "team": "platform",
                "labels": ["bug", "incident", "maintenance"],
                "output_artifacts": ["src/api/retry.py", "tests/test_retry.py"],
                "input_artifacts": ["issues/BUG-142.md"],
            },
            facets={
                "git": {
                    "repository": "product-api",
                    "branch": "fix/bug-142-timeouts",
                    "issue_labels": ["bug", "incident", "maintenance"],
                    "files_touched": ["src/api/retry.py", "tests/test_retry.py"],
                    "diff_stats": {"added": 34, "deleted": 8},
                    "deployment_target": "production",
                }
            },
        ),
        _event(
            trace_id=trace_maintenance,
            span_id="span_retriever_bug",
            parent_span_id="span_root_bug",
            span_kind=SpanKind.RETRIEVER,
            name="Inspect related incidents",
            start=base + timedelta(seconds=1),
            duration_ms=2_000,
            direct_cost=0.0,
            attributes={"issue_id": "BUG-142", "labels": ["bug", "maintenance"]},
        ),
        _event(
            trace_id=trace_maintenance,
            span_id="span_tool_bug",
            parent_span_id="span_root_bug",
            span_kind=SpanKind.TOOL,
            name="Inspect failing test traces",
            start=base + timedelta(seconds=2),
            duration_ms=4_000,
            direct_cost=0.0,
            tool_name="pytest",
            attributes={"issue_id": "BUG-142", "labels": ["bug", "maintenance"]},
        ),
        _event(
            trace_id=trace_maintenance,
            span_id="span_llm_bug",
            parent_span_id="span_root_bug",
            span_kind=SpanKind.LLM,
            name="Generate patch candidate",
            start=base + timedelta(seconds=7),
            duration_ms=9_000,
            direct_cost=0.024,
            token_input=1400,
            token_output=880,
            model_name="gpt-4.1",
            attributes={"issue_id": "BUG-142", "labels": ["bug", "maintenance"]},
        ),
        _event(
            trace_id=trace_maintenance,
            span_id="span_guardrail_bug",
            parent_span_id="span_root_bug",
            span_kind=SpanKind.GUARDRAIL,
            name="Run merge policy checks",
            start=base + timedelta(seconds=16),
            duration_ms=1_500,
            direct_cost=0.0,
            attributes={"issue_id": "BUG-142", "review_required": True},
        ),
        _event(
            trace_id=trace_maintenance,
            span_id="span_review_bug",
            parent_span_id="span_root_bug",
            span_kind=SpanKind.REVIEW,
            name="Human review and merge approval",
            start=base + timedelta(seconds=18),
            duration_ms=3_000,
            direct_cost=0.0,
            attributes={"issue_id": "BUG-142", "review_required": True, "actor": "eng-reviewer"},
        ),
        _event(
            trace_id=trace_feature,
            span_id="span_root_feat",
            parent_span_id=None,
            span_kind=SpanKind.AGENT,
            name="Build workflow orchestration dashboard",
            start=base + timedelta(minutes=6),
            duration_ms=31_000,
            direct_cost=0.031,
            token_input=1750,
            token_output=1240,
            model_name="gpt-4.1",
            attributes={
                "issue_id": "FEAT-77",
                "task_title": "Implement orchestration dashboard for customers",
                "objective": "Add new workflow observability dashboard to external product",
                "project": "product-control-plane",
                "team": "app-platform",
                "labels": ["feature", "product"],
                "output_artifacts": ["src/dashboard/page.tsx", "src/dashboard/charts.tsx"],
                "input_artifacts": ["issues/FEAT-77.md"],
            },
            facets={
                "git": {
                    "repository": "product-control-plane",
                    "branch": "feat/orchestration-dashboard",
                    "issue_labels": ["feature", "product"],
                    "files_touched": ["src/dashboard/page.tsx", "src/dashboard/charts.tsx"],
                    "diff_stats": {"added": 220, "deleted": 27},
                    "deployment_target": "staging",
                }
            },
        ),
        _event(
            trace_id=trace_feature,
            span_id="span_retriever_feat",
            parent_span_id="span_root_feat",
            span_kind=SpanKind.RETRIEVER,
            name="Gather customer usage requirements",
            start=base + timedelta(minutes=6, seconds=4),
            duration_ms=2_500,
            direct_cost=0.0,
            attributes={"issue_id": "FEAT-77", "labels": ["feature", "product"]},
        ),
        _event(
            trace_id=trace_feature,
            span_id="span_llm_feat",
            parent_span_id="span_root_feat",
            span_kind=SpanKind.LLM,
            name="Generate React component batch",
            start=base + timedelta(minutes=6, seconds=9),
            duration_ms=12_000,
            direct_cost=0.041,
            token_input=2100,
            token_output=1720,
            model_name="gpt-4.1",
            attributes={"issue_id": "FEAT-77", "labels": ["feature", "product"]},
        ),
        _event(
            trace_id=trace_feature,
            span_id="span_tool_feat",
            parent_span_id="span_root_feat",
            span_kind=SpanKind.TOOL,
            name="Run component tests",
            start=base + timedelta(minutes=6, seconds=23),
            duration_ms=4_500,
            direct_cost=0.0,
            tool_name="vitest",
            attributes={"issue_id": "FEAT-77"},
        ),
        _event(
            trace_id=trace_feature,
            span_id="span_eval_feat",
            parent_span_id="span_root_feat",
            span_kind=SpanKind.EVALUATOR,
            name="Score dashboard accessibility coverage",
            start=base + timedelta(minutes=6, seconds=26),
            duration_ms=1_500,
            direct_cost=0.0,
            attributes={"issue_id": "FEAT-77"},
        ),
        _event(
            trace_id=trace_internal,
            span_id="span_root_internal",
            parent_span_id=None,
            span_kind=SpanKind.AGENT,
            name="Automate internal release workflow",
            start=base + timedelta(minutes=12),
            duration_ms=24_000,
            direct_cost=0.022,
            token_input=1000,
            token_output=760,
            model_name="gpt-4.1",
            attributes={
                "task_title": "Automate release checklist workflow",
                "objective": "Deliver an internal tool for release automation",
                "project": "developer-experience",
                "team": "platform",
                "labels": ["internal-tool", "ops"],
                "output_artifacts": ["src/release/workflow.ts", "src/release/approval.ts"],
                "input_artifacts": ["docs/release-checklist.md"],
            },
            facets={
                "git": {
                    "repository": "internal-release-tools",
                    "branch": "feat/release-automation",
                    "issue_labels": ["internal-tool", "ops"],
                    "files_touched": ["src/release/workflow.ts", "src/release/approval.ts"],
                    "diff_stats": {"added": 180, "deleted": 24},
                    "deployment_target": "internal",
                }
            },
        ),
        _event(
            trace_id=trace_internal,
            span_id="span_eval_internal",
            parent_span_id="span_root_internal",
            span_kind=SpanKind.EVALUATOR,
            name="Score rollout safety",
            start=base + timedelta(minutes=12, seconds=6),
            duration_ms=4_000,
            direct_cost=0.0,
            attributes={"task_title": "Automate release checklist workflow"},
        ),
        _event(
            trace_id=trace_internal,
            span_id="span_llm_internal",
            parent_span_id="span_root_internal",
            span_kind=SpanKind.LLM,
            name="Draft workflow automation plan",
            start=base + timedelta(minutes=12, seconds=12),
            duration_ms=8_000,
            direct_cost=0.019,
            token_input=1220,
            token_output=1010,
            model_name="gpt-4.1",
            attributes={"labels": ["internal-tool", "ops"]},
        ),
    ]


def marketing_demo_events() -> list[dict[str, Any]]:
    base = datetime(2026, 4, 6, 13, 15, tzinfo=UTC)
    trace_id = new_id("trace")
    return [
        _event(
            trace_id=trace_id,
            span_id="span_root_marketing",
            parent_span_id=None,
            span_kind=SpanKind.AGENT,
            name="Generate Q2 launch campaign copy",
            start=base,
            duration_ms=18_000,
            direct_cost=0.011,
            token_input=900,
            token_output=820,
            model_name="gpt-4.1-mini",
            attributes={
                "campaign_id": "CMP-2026-Q2-LAUNCH",
                "task_title": "Draft launch copy for paid social and email",
                "objective": "Produce campaign assets for Q2 launch",
                "project": "growth",
                "team": "marketing",
                "labels": ["marketing", "campaign"],
                "output_artifacts": [
                    "artifacts/q2-launch-ad-copy.md",
                    "artifacts/q2-launch-email.md",
                ],
            },
            facets={
                "marketing": {
                    "channel": "paid_social",
                    "destination_system": "hubspot",
                    "campaign_name": "Q2 Launch",
                }
            },
        ),
        _event(
            trace_id=trace_id,
            span_id="span_llm_marketing",
            parent_span_id="span_root_marketing",
            span_kind=SpanKind.LLM,
            name="Draft copy variants",
            start=base + timedelta(seconds=4),
            duration_ms=7_500,
            direct_cost=0.022,
            token_input=1300,
            token_output=1400,
            model_name="gpt-4.1",
            attributes={"campaign_id": "CMP-2026-Q2-LAUNCH", "labels": ["marketing", "campaign"]},
        ),
        _event(
            trace_id=trace_id,
            span_id="span_review_marketing",
            parent_span_id="span_root_marketing",
            span_kind=SpanKind.REVIEW,
            name="Brand review",
            start=base + timedelta(seconds=14),
            duration_ms=2_000,
            direct_cost=0.0,
            attributes={"campaign_id": "CMP-2026-Q2-LAUNCH", "actor": "brand-reviewer"},
        ),
    ]


def support_demo_events() -> list[dict[str, Any]]:
    base = datetime(2026, 4, 6, 14, 5, tzinfo=UTC)
    reviewed_trace = new_id("trace")
    unreviewed_trace = new_id("trace")
    return [
        _event(
            trace_id=reviewed_trace,
            span_id="span_root_support_reviewed",
            parent_span_id=None,
            span_kind=SpanKind.AGENT,
            name="Draft resolution for ticket CS-2048",
            start=base,
            duration_ms=16_000,
            direct_cost=0.009,
            token_input=750,
            token_output=690,
            model_name="gpt-4.1-mini",
            attributes={
                "ticket_id": "CS-2048",
                "task_title": "Resolve billing export issue",
                "objective": "Prepare customer-facing resolution and handoff steps",
                "project": "support",
                "team": "customer-success",
                "labels": ["support", "billing"],
                "output_artifacts": ["tickets/CS-2048-response.md"],
            },
            facets={
                "support": {
                    "ticket_id": "CS-2048",
                    "destination_system": "zendesk",
                    "customer_facing": True,
                }
            },
        ),
        _event(
            trace_id=reviewed_trace,
            span_id="span_review_support_reviewed",
            parent_span_id="span_root_support_reviewed",
            span_kind=SpanKind.REVIEW,
            name="Support lead review",
            start=base + timedelta(seconds=11),
            duration_ms=2_500,
            direct_cost=0.0,
            attributes={"ticket_id": "CS-2048", "actor": "support-lead"},
        ),
        _event(
            trace_id=unreviewed_trace,
            span_id="span_root_support_unreviewed",
            parent_span_id=None,
            span_kind=SpanKind.AGENT,
            name="Draft response for ticket CS-2051",
            start=base + timedelta(minutes=4),
            duration_ms=10_000,
            direct_cost=0.007,
            token_input=620,
            token_output=510,
            model_name="gpt-4.1-mini",
            attributes={
                "ticket_id": "CS-2051",
                "task_title": "Reply to API key reset question",
                "objective": "Produce customer-facing answer for API key reset",
                "project": "support",
                "team": "customer-success",
                "labels": ["support"],
                "output_artifacts": ["tickets/CS-2051-response.md"],
            },
            facets={
                "support": {
                    "ticket_id": "CS-2051",
                    "destination_system": "zendesk",
                    "customer_facing": True,
                }
            },
        ),
    ]


def demo_events(name: str) -> list[dict[str, Any]]:
    mapping = {
        "capex": coding_demo_events,
        "agent-cost": coding_demo_events,
        "coding": coding_demo_events,
        "marketing": marketing_demo_events,
        "support": support_demo_events,
    }
    if name == "all":
        events: list[dict[str, Any]] = []
        for key in ("coding", "marketing", "support"):
            events.extend(mapping[key]())
        return events
    return mapping[name]()


def write_demo_file(name: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(event) for event in demo_events(name))
    destination.write_text(payload + "\n", encoding="utf-8")
    return destination


def run_demo(name: str, project_dir: Path, policy_path: Path | None = None) -> dict[str, Any]:
    if name in HF_DEMOS:
        return run_hf_demo(name, project_dir, policy_path=policy_path)
    config = WorkledgerConfig.from_project_dir(project_dir)
    pipeline = WorkledgerPipeline(config)
    raw_events_dir = config.raw_events_dir
    policies_dir = config.policies_dir
    assert raw_events_dir is not None
    assert policies_dir is not None
    input_path = write_demo_file(name, raw_events_dir / f"{name}.jsonl")
    ingest_result = pipeline.ingest(input_path)
    work_units = pipeline.rollup()
    policy_path = (
        policies_dir / "software_capex_review_v1.yaml"
        if name == "capex" and policy_path is None
        else policy_path
    )
    classifications = pipeline.classify(policy_path)
    include_economics = name in {"all", "agent-cost", "coding"}
    reports = pipeline.report(include_economics=include_economics)
    summary = pipeline.report_engine.summary(include_economics=include_economics)
    review_queue = pipeline.review_queue()
    pipeline.close()
    return {
        "input_path": str(input_path),
        "ingest": ingest_result.model_dump(mode="json"),
        "work_units": [item.model_dump(mode="json") for item in work_units],
        "classifications": [item.model_dump(mode="json") for item in classifications],
        "reports": [item.model_dump(mode="json") for item in reports],
        "summary": summary,
        "review_queue": review_queue,
    }


def run_hf_demo(name: str, project_dir: Path, policy_path: Path | None = None) -> dict[str, Any]:
    config = WorkledgerConfig.from_project_dir(project_dir)
    pipeline = WorkledgerPipeline(config)
    demo = HF_DEMOS[name]
    ingest_result = pipeline.ingest_huggingface(
        demo["dataset_id"],
        adapter_name=demo["adapter"],
        split=demo["split"],
        limit=demo["limit"],
        seed=demo["seed"],
    )
    work_units = pipeline.rollup()
    classifications = pipeline.classify(policy_path) if policy_path is not None else []
    reports = pipeline.report(include_economics=bool(demo["include_economics"]))
    summary = pipeline.report_engine.summary(include_economics=bool(demo["include_economics"]))
    review_queue = pipeline.review_queue()
    pipeline.close()
    return {
        "dataset_id": ingest_result.dataset_id,
        "adapter_name": ingest_result.adapter_name,
        "split": ingest_result.split,
        "input_path": str(ingest_result.raw_path),
        "ingest": ingest_result.ingest.model_dump(mode="json"),
        "work_units": [item.model_dump(mode="json") for item in work_units],
        "classifications": [item.model_dump(mode="json") for item in classifications],
        "reports": [item.model_dump(mode="json") for item in reports],
        "summary": summary,
        "review_queue": review_queue,
    }
