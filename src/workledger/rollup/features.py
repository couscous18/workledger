from __future__ import annotations

from collections import Counter
from typing import Any

from workledger.models import (
    ActorKind,
    ImportanceBand,
    ObservationSpan,
    ReviewState,
    SpanKind,
    TrustState,
)

PRIMARY_SPAN_KINDS = {SpanKind.LLM, SpanKind.AGENT, SpanKind.REVIEW, SpanKind.ROOT}
SUPPRESSED_SPAN_KINDS = {SpanKind.RETRIEVER, SpanKind.GUARDRAIL, SpanKind.EVALUATOR}

# Importance scoring weights — controls how direct_cost, duration, and
# qualitative signals contribute to the 0–1 importance score.
COST_WEIGHT = 8.0
DURATION_DIVISOR_MS = 120_000.0
REVIEW_BONUS = 0.15
OUTPUT_BONUS = 0.1
SIGNAL_BONUS_PER_PRIMARY = 0.05


def choose_primary_spans(spans: list[ObservationSpan]) -> list[ObservationSpan]:
    primary = [span for span in spans if span.span_kind in PRIMARY_SPAN_KINDS]
    return primary or spans


def infer_kind(spans: list[ObservationSpan]) -> str:
    for span in spans:
        if "support" in span.facets or span.attributes.get("ticket_id"):
            return "support_resolution"
        if "marketing" in span.facets or span.attributes.get("campaign_id"):
            return "marketing_generation"
        if "git" in span.facets or span.attributes.get("issue_id"):
            return "software_delivery"
        for _key, value in {**span.attributes, **span.facets}.items():
            if isinstance(value, str):
                lowered = value.lower()
                if "support" in lowered or "ticket" in lowered:
                    return "support_resolution"
                if "campaign" in lowered or "marketing" in lowered:
                    return "marketing_generation"
                if "repo" in lowered or "feature" in lowered or "bug" in lowered:
                    return "software_delivery"
    kinds = Counter(span.span_kind for span in spans)
    if kinds.get(SpanKind.REVIEW):
        return "reviewed_ai_work"
    if kinds.get(SpanKind.TOOL):
        return "augmented_ai_work"
    return "ai_work"


def infer_actor_kind(spans: list[ObservationSpan]) -> ActorKind:
    has_review = any(span.span_kind == SpanKind.REVIEW for span in spans)
    has_agent = any(span.span_kind in {SpanKind.AGENT, SpanKind.LLM} for span in spans)
    if has_review and has_agent:
        return ActorKind.HYBRID
    if has_review:
        return ActorKind.HUMAN
    if has_agent:
        return ActorKind.AGENT
    return ActorKind.SERVICE


def infer_review_state(spans: list[ObservationSpan]) -> ReviewState:
    if any(span.span_kind == SpanKind.REVIEW for span in spans):
        return ReviewState.REVIEWED
    if any(bool(span.attributes.get("review_required")) for span in spans):
        return ReviewState.QUEUED
    return ReviewState.UNREVIEWED


def infer_trust_state(spans: list[ObservationSpan], review_state: ReviewState) -> TrustState:
    if review_state == ReviewState.REVIEWED:
        return TrustState.HUMAN_REVIEWED
    if any(bool(span.attributes.get("self_checked")) for span in spans):
        return TrustState.SELF_CHECKED
    return TrustState.UNREVIEWED


def infer_title(spans: list[ObservationSpan]) -> str:
    primary = choose_primary_spans(spans)
    for span in primary:
        if title := span.attributes.get("title"):
            return str(title)
        if title := span.attributes.get("task_title"):
            return str(title)
        if title := span.attributes.get("objective"):
            return str(title)
    if primary:
        return primary[0].name
    return "untitled"


def infer_summary(spans: list[ObservationSpan]) -> str:
    primary = choose_primary_spans(spans)
    if not primary:
        return f"Empty work unit with {len(spans)} spans."
    focus = primary[0]
    tokens = sum(span.token_input + span.token_output for span in spans)
    tools = sorted({span.tool_name for span in spans if span.tool_name})
    tool_text = ", ".join(tools) if tools else "no tools"
    return f"{focus.name} across {len(spans)} spans, {tokens} tokens, using {tool_text}."


def infer_objective(spans: list[ObservationSpan]) -> str | None:
    for span in choose_primary_spans(spans):
        for key in ("objective", "prompt_summary", "task", "request"):
            if value := span.attributes.get(key):
                return str(value)
    return None


def infer_artifacts(spans: list[ObservationSpan], key: str) -> list[str]:
    artifacts: list[str] = []
    for span in spans:
        value = span.attributes.get(key)
        if isinstance(value, list):
            artifacts.extend(str(item) for item in value)
        elif isinstance(value, str):
            artifacts.append(value)
    return sorted(set(artifacts))


def importance_score(spans: list[ObservationSpan]) -> float:
    direct_cost = sum(span.direct_cost for span in spans)
    duration_ms = sum(span.duration_ms for span in choose_primary_spans(spans))
    reviewed_bonus = REVIEW_BONUS if any(span.span_kind == SpanKind.REVIEW for span in spans) else 0.0
    output_bonus = OUTPUT_BONUS if infer_artifacts(spans, "output_artifacts") else 0.0
    signal_bonus = SIGNAL_BONUS_PER_PRIMARY * len(choose_primary_spans(spans))
    score = min(
        1.0,
        direct_cost * COST_WEIGHT + (duration_ms / DURATION_DIVISOR_MS) + reviewed_bonus + output_bonus + signal_bonus,
    )
    return round(score, 3)


def importance_band(score: float) -> ImportanceBand:
    if score >= 0.85:
        return ImportanceBand.CRITICAL
    if score >= 0.55:
        return ImportanceBand.HIGH
    if score >= 0.25:
        return ImportanceBand.MEDIUM
    return ImportanceBand.LOW


def summarize_sources(spans: list[ObservationSpan]) -> list[str]:
    return sorted({str(span.source_kind) for span in spans})


def merge_facets(spans: list[ObservationSpan]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for span in spans:
        for namespace, payload in span.facets.items():
            if namespace not in merged:
                merged[namespace] = payload
            elif isinstance(merged[namespace], dict) and isinstance(payload, dict):
                merged[namespace] = {**merged[namespace], **payload}
    return merged
