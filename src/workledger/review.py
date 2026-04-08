"""Review queue prioritization for ambiguous or high-importance work units."""

from __future__ import annotations

from typing import Any

from workledger.models import PolicyOutcome, ReviewOverride, WorkCategory
from workledger.storage import DuckDBStore

# Priority scoring weights — controls how importance, cost, and confidence
# contribute to the review queue ranking.
IMPORTANCE_WEIGHT = 5.0
COST_WEIGHT = 40.0
UNCERTAINTY_WEIGHT = 2.5
COMPETING_BONUS = 0.5


def _top_competing_candidates(work_unit_id: str, decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for decision in decisions:
        if decision.get("trace_id") == work_unit_id or decision.get("trace_id") is None:
            candidates = decision.get("competing_candidates", [])
            if isinstance(candidates, list):
                return [item for item in candidates if isinstance(item, dict)]
    return []


def review_queue_items(store: DuckDBStore, limit: int | None = None) -> list[dict[str, Any]]:
    work_units = {item.work_unit_id: item for item in store.list_work_units()}
    queue: list[dict[str, Any]] = []
    for trace in store.list_classifications():
        if not trace.reviewer_required or trace.reviewer_status != "pending":
            continue
        work_unit = work_units.get(trace.work_unit_id)
        if work_unit is None:
            continue
        competing_candidates = _top_competing_candidates(
            trace.work_unit_id,
            [decision.model_dump(mode="json") for decision in trace.decisions],
        )
        top_gap = None
        if competing_candidates:
            top_gap = round(
                abs(trace.confidence_score - float(competing_candidates[0].get("confidence", 0.0))),
                3,
            )
        priority_score = round(
            (work_unit.importance_score * IMPORTANCE_WEIGHT)
            + (trace.blended_cost * COST_WEIGHT)
            + ((1.0 - trace.confidence_score) * UNCERTAINTY_WEIGHT)
            + (COMPETING_BONUS if competing_candidates else 0.0),
            3,
        )
        queue.append(
            {
                "review_priority_score": priority_score,
                "work_unit_id": work_unit.work_unit_id,
                "classification_id": trace.classification_id,
                "title": work_unit.title,
                "project": work_unit.project,
                "work_category": trace.work_category,
                "policy_outcome": trace.policy_outcome,
                "blended_cost": trace.blended_cost,
                "confidence_score": trace.confidence_score,
                "evidence_score": trace.evidence_score,
                "importance_score": work_unit.importance_score,
                "importance_band": work_unit.importance_band,
                "source_span_count": len(work_unit.source_span_ids),
                "compression_ratio": work_unit.compression_ratio,
                "reviewer_status": trace.reviewer_status,
                "override_status": trace.override_status,
                "competing_candidates": competing_candidates,
                "confidence_gap": top_gap,
            }
        )
    queue.sort(
        key=lambda item: (
            item["review_priority_score"],
            item["importance_score"],
            item["blended_cost"],
            -item["confidence_score"],
        ),
        reverse=True,
    )
    return queue[:limit] if limit is not None else queue


def apply_override(
    store: DuckDBStore,
    classification_id: str,
    reviewer: str,
    note: str,
    work_category: str | None = None,
    policy_outcome: str | None = None,
) -> ReviewOverride:
    trace = store.get_classification(classification_id)
    if trace is None:
        raise ValueError(f"unknown classification: {classification_id}")
    override = ReviewOverride(
        classification_id=classification_id,
        reviewer=reviewer,
        note=note,
        work_category=WorkCategory(work_category) if work_category else None,
        policy_outcome=PolicyOutcome(policy_outcome)
        if policy_outcome
        else None,
    )
    updated_work_category = override.work_category or trace.work_category
    updated_policy_outcome = override.policy_outcome or trace.policy_outcome
    updated_explanation = (
        f"{trace.explanation} Reviewer override by {reviewer}: {note}"
    )
    updated_decisions = trace.decisions
    if updated_decisions:
        updated_decisions = [
            updated_decisions[0].model_copy(
                update={
                    "value": str(updated_work_category),
                    "explanation": updated_explanation,
                    "requires_review": False,
                    "competing_candidates": [],
                }
            ),
            *updated_decisions[1:],
        ]
    updated = trace.model_copy(
        update={
            "work_category": updated_work_category,
            "policy_outcome": updated_policy_outcome,
            "explanation": updated_explanation,
            "override_status": "applied",
            "reviewer_status": "overridden",
            "policy_hint": f"{updated_work_category}:{updated_policy_outcome}:overridden",
            "decisions": updated_decisions,
        }
    )
    store.save_override(override)
    store.save_classifications([updated])
    return override
