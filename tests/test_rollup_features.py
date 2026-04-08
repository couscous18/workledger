"""Tests for rollup feature inference functions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from workledger.models import ActorKind, ImportanceBand, ObservationSpan, ReviewState, TrustState
from workledger.rollup.features import (
    choose_primary_spans,
    importance_band,
    importance_score,
    infer_actor_kind,
    infer_artifacts,
    infer_kind,
    infer_review_state,
    infer_summary,
    infer_title,
    infer_trust_state,
    merge_facets,
    summarize_sources,
)


def _span(
    *,
    name: str = "test-span",
    span_kind: str = "llm",
    attributes: dict | None = None,
    facets: dict | None = None,
    direct_cost: float = 0.0,
    token_input: int = 100,
    token_output: int = 50,
    duration_seconds: int = 5,
) -> ObservationSpan:
    start = datetime(2026, 4, 6, tzinfo=UTC)
    end = start + timedelta(seconds=duration_seconds)
    return ObservationSpan.model_validate(
        {
            "source_kind": "sdk",
            "trace_id": "t1",
            "span_id": "s1",
            "span_kind": span_kind,
            "name": name,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "token_input": token_input,
            "token_output": token_output,
            "direct_cost": direct_cost,
            "attributes": attributes or {},
            "facets": facets or {},
        }
    )


# --- choose_primary_spans ---


def test_choose_primary_spans_prefers_llm_and_agent() -> None:
    llm = _span(span_kind="llm", name="llm")
    tool = _span(span_kind="tool", name="tool")
    primary = choose_primary_spans([llm, tool])
    assert [s.name for s in primary] == ["llm"]


def test_choose_primary_spans_falls_back_to_all() -> None:
    tool = _span(span_kind="tool", name="tool")
    retriever = _span(span_kind="retriever", name="retriever")
    primary = choose_primary_spans([tool, retriever])
    assert len(primary) == 2


# --- infer_kind ---


def test_infer_kind_detects_support_from_facets() -> None:
    span = _span(facets={"support": {"ticket_id": "T-1"}})
    assert infer_kind([span]) == "support_resolution"


def test_infer_kind_detects_software_from_git_facets() -> None:
    span = _span(facets={"git": {"repository": "org/repo"}})
    assert infer_kind([span]) == "software_delivery"


def test_infer_kind_detects_marketing_from_attributes() -> None:
    span = _span(attributes={"campaign_id": "C-1"})
    assert infer_kind([span]) == "marketing_generation"


def test_infer_kind_defaults_to_ai_work() -> None:
    span = _span()
    assert infer_kind([span]) == "ai_work"


def test_infer_kind_review_spans_classified_as_reviewed() -> None:
    span = _span(span_kind="review")
    assert infer_kind([span]) == "reviewed_ai_work"


def test_infer_kind_tool_spans_classified_as_augmented() -> None:
    span = _span(span_kind="tool")
    assert infer_kind([span]) == "augmented_ai_work"


# --- infer_actor_kind ---


def test_infer_actor_kind_hybrid() -> None:
    review = _span(span_kind="review")
    agent = _span(span_kind="agent")
    assert infer_actor_kind([review, agent]) == ActorKind.HYBRID


def test_infer_actor_kind_agent_only() -> None:
    assert infer_actor_kind([_span(span_kind="llm")]) == ActorKind.AGENT


def test_infer_actor_kind_human_only() -> None:
    assert infer_actor_kind([_span(span_kind="review")]) == ActorKind.HUMAN


def test_infer_actor_kind_service_fallback() -> None:
    assert infer_actor_kind([_span(span_kind="tool")]) == ActorKind.SERVICE


# --- infer_review_state / infer_trust_state ---


def test_infer_review_state_reviewed() -> None:
    assert infer_review_state([_span(span_kind="review")]) == ReviewState.REVIEWED


def test_infer_review_state_queued() -> None:
    span = _span(attributes={"review_required": True})
    assert infer_review_state([span]) == ReviewState.QUEUED


def test_infer_review_state_unreviewed() -> None:
    assert infer_review_state([_span()]) == ReviewState.UNREVIEWED


def test_infer_trust_state_human_reviewed() -> None:
    assert infer_trust_state([_span()], ReviewState.REVIEWED) == TrustState.HUMAN_REVIEWED


def test_infer_trust_state_self_checked() -> None:
    span = _span(attributes={"self_checked": True})
    assert infer_trust_state([span], ReviewState.UNREVIEWED) == TrustState.SELF_CHECKED


def test_infer_trust_state_unreviewed() -> None:
    assert infer_trust_state([_span()], ReviewState.UNREVIEWED) == TrustState.UNREVIEWED


# --- infer_title ---


def test_infer_title_from_attribute() -> None:
    span = _span(attributes={"title": "Fix auth bug"})
    assert infer_title([span]) == "Fix auth bug"


def test_infer_title_falls_back_to_name() -> None:
    span = _span(name="my-span")
    assert infer_title([span]) == "my-span"


def test_infer_title_empty_spans_returns_untitled() -> None:
    assert infer_title([]) == "untitled"


# --- infer_summary ---


def test_infer_summary_includes_token_count() -> None:
    span = _span(token_input=200, token_output=100)
    summary = infer_summary([span])
    assert "300 tokens" in summary


def test_infer_summary_empty_spans() -> None:
    assert infer_summary([]) == "Empty work unit with 0 spans."


# --- infer_artifacts ---


def test_infer_artifacts_collects_from_list_and_string() -> None:
    s1 = _span(attributes={"output_artifacts": ["a.py", "b.py"]})
    s2 = _span(attributes={"output_artifacts": "c.py"})
    artifacts = infer_artifacts([s1, s2], "output_artifacts")
    assert artifacts == ["a.py", "b.py", "c.py"]


def test_infer_artifacts_deduplicates() -> None:
    s1 = _span(attributes={"output_artifacts": ["a.py"]})
    s2 = _span(attributes={"output_artifacts": "a.py"})
    assert infer_artifacts([s1, s2], "output_artifacts") == ["a.py"]


# --- importance_score ---


def test_importance_score_zero_cost_low() -> None:
    span = _span(direct_cost=0.0, duration_seconds=1)
    score = importance_score([span])
    assert 0.0 <= score <= 1.0
    assert score < 0.5


def test_importance_score_high_cost_near_max() -> None:
    span = _span(direct_cost=0.5, duration_seconds=60)
    score = importance_score([span])
    assert score == 1.0


def test_importance_score_clamped_at_one() -> None:
    span = _span(direct_cost=10.0)
    assert importance_score([span]) == 1.0


# --- importance_band ---


def test_importance_band_critical() -> None:
    assert importance_band(0.9) == ImportanceBand.CRITICAL


def test_importance_band_high() -> None:
    assert importance_band(0.6) == ImportanceBand.HIGH


def test_importance_band_medium() -> None:
    assert importance_band(0.3) == ImportanceBand.MEDIUM


def test_importance_band_low() -> None:
    assert importance_band(0.1) == ImportanceBand.LOW


# --- summarize_sources ---


def test_summarize_sources_deduplicates() -> None:
    s1 = _span()
    s2 = _span()
    assert summarize_sources([s1, s2]) == ["sdk"]


# --- merge_facets ---


def test_merge_facets_combines_namespaces() -> None:
    s1 = _span(facets={"git": {"repo": "org/a"}})
    s2 = _span(facets={"support": {"ticket_id": "T-1"}})
    merged = merge_facets([s1, s2])
    assert "git" in merged
    assert "support" in merged


def test_merge_facets_merges_dicts_in_same_namespace() -> None:
    s1 = _span(facets={"git": {"repo": "org/a"}})
    s2 = _span(facets={"git": {"branch": "main"}})
    merged = merge_facets([s1, s2])
    assert merged["git"] == {"repo": "org/a", "branch": "main"}
