from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast

from workledger.models import (
    ClassificationTrace,
    EvidenceStrength,
    PolicyDecision,
    PolicyOutcome,
    PolicyPack,
    PolicyRun,
    WorkCategory,
    WorkUnit,
)
from workledger.utils.ids import stable_id

# Confidence blending — controls how much the rule match confidence vs.
# the evidence quality score contribute to the final confidence.
RULE_CONFIDENCE_WEIGHT = 0.7
EVIDENCE_CONFIDENCE_WEIGHT = 0.3

# When the gap between the top two competing decisions is smaller than
# this threshold, a human reviewer is required.
COMPETING_GAP_THRESHOLD = 0.15


def _flatten(prefix: str, value: Any, target: dict[str, Any]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else key
            _flatten(next_prefix, child, target)
    else:
        target[prefix] = value


def extract_features(work_unit: WorkUnit) -> dict[str, Any]:
    features: dict[str, Any] = {
        "kind": work_unit.kind,
        "title": work_unit.title,
        "summary": work_unit.summary,
        "objective": work_unit.objective,
        "actor_kind": work_unit.actor_kind,
        "project": work_unit.project,
        "team": work_unit.team,
        "cost_center": work_unit.cost_center,
        "review_state": work_unit.review_state,
        "trust_state": work_unit.trust_state,
        "importance_score": work_unit.importance_score,
        "importance_band": work_unit.importance_band,
        "source_systems": work_unit.source_systems,
        "labels": work_unit.labels,
        "output_artifact_refs": work_unit.output_artifact_refs,
        "input_artifact_refs": work_unit.input_artifact_refs,
        "has_human_review": work_unit.review_state == "reviewed",
        "has_output_artifacts": bool(work_unit.output_artifact_refs),
        "compression_ratio": work_unit.compression_ratio,
        "evidence_count": len(work_unit.evidence_bundle),
        "direct_cost": work_unit.direct_cost,
        "total_cost": work_unit.total_cost,
        "duration_ms": work_unit.duration_ms,
    }
    for key, value in work_unit.facets.items():
        _flatten(key, value, features)
    return features


def _contains(collection: Any, value: Any) -> bool:
    if isinstance(collection, str):
        return str(value).lower() in collection.lower()
    if isinstance(collection, Iterable):
        return value in collection
    return False


def _evaluate_condition(features: dict[str, Any], condition: dict[str, Any]) -> bool:
    feature_name = condition["feature"]
    actual = features.get(feature_name)
    operator = condition.get("op", "eq")
    expected = condition.get("value")
    if operator == "eq":
        return actual == expected
    if operator == "neq":
        return actual != expected
    if operator == "contains":
        return _contains(actual, expected)
    if operator == "in":
        return actual in list(expected or [])
    if operator == "overlaps":
        actual_values = set(actual or [])
        expected_values = set(expected or [])
        return bool(actual_values & expected_values)
    if operator == "exists":
        return actual is not None
    if operator == "gte":
        return float(actual if actual is not None else 0.0) >= float(
            expected if expected is not None else 0.0
        )
    if operator == "lte":
        return float(actual if actual is not None else 0.0) <= float(
            expected if expected is not None else 0.0
        )
    raise ValueError(f"unsupported operator: {operator}")


def _matches_rule(features: dict[str, Any], rule: dict[str, Any]) -> bool:
    when = rule.get("when", {})
    all_conditions = when.get("all", [])
    any_conditions = when.get("any", [])
    if all_conditions and not all(
        _evaluate_condition(features, condition) for condition in all_conditions
    ):
        return False
    return not (
        any_conditions
        and not any(_evaluate_condition(features, condition) for condition in any_conditions)
    )


def _evidence_score(work_unit: WorkUnit, features: dict[str, Any]) -> float:
    score = 0.1
    if features.get("has_output_artifacts"):
        score += 0.25
    if features.get("has_human_review"):
        score += 0.3
    if features.get("git.repository"):
        score += 0.15
    if features.get("marketing.channel") or features.get("support.ticket_id"):
        score += 0.15
    if features.get("git.issue_labels") or features.get("campaign_id"):
        score += 0.1
    return min(1.0, round(score, 3))


def _evidence_strength(score: float) -> EvidenceStrength:
    if score >= 0.9:
        return EvidenceStrength.VERIFIED
    if score >= 0.65:
        return EvidenceStrength.STRONG
    if score >= 0.35:
        return EvidenceStrength.MODERATE
    return EvidenceStrength.WEAK


def _policy_hint(work_category: str, policy_outcome: str) -> str:
    return f"{work_category}:{policy_outcome}:candidate_only"


class PolicyEngine:
    def classify(
        self, work_units: list[WorkUnit], pack: PolicyPack
    ) -> tuple[list[ClassificationTrace], PolicyRun]:
        traces = [self.classify_one(work_unit, pack) for work_unit in work_units]
        policy_run = PolicyRun(
            policy_basis=pack.basis,
            trace_count=len(traces),
            review_required_count=sum(1 for trace in traces if trace.reviewer_required),
            notes=f"policy pack {pack.policy_pack_id} v{pack.version}",
        )
        return traces, policy_run

    def classify_one(self, work_unit: WorkUnit, pack: PolicyPack) -> ClassificationTrace:
        features = extract_features(work_unit)
        matched_rules = sorted(
            (rule for rule in pack.rules if _matches_rule(features, rule)),
            key=lambda rule: int(rule.get("priority", 0)),
            reverse=True,
        )
        decisions = [self._decision_from_rule(work_unit, features, rule) for rule in matched_rules]
        top_decision = (
            decisions[0] if decisions else self._default_decision(work_unit, pack, features)
        )
        competing = [
            {
                "rule_id": decision.rule_id,
                "value": decision.value,
                "confidence": decision.confidence,
            }
            for decision in decisions[1:4]
        ]
        if competing:
            top_decision = top_decision.model_copy(update={"competing_candidates": competing})
        evidence_score = _evidence_score(work_unit, features)
        confidence = min(
            1.0,
            round(
                (top_decision.confidence * RULE_CONFIDENCE_WEIGHT)
                + (evidence_score * EVIDENCE_CONFIDENCE_WEIGHT),
                3,
            ),
        )
        reviewer_required = bool(
            top_decision.requires_review
            or confidence < 0.7
            or evidence_score < 0.45
            or (
                competing
                and abs(
                    top_decision.confidence
                    - float(cast(float, competing[0].get("confidence", 0.0)))
                )
                < COMPETING_GAP_THRESHOLD
            )
        )
        work_category = WorkCategory(top_decision.value)
        policy_outcome = PolicyOutcome(
            matched_rules[0]["decision"].get(
                "policy_outcome", pack.default_policy_outcome
            )
            if matched_rules
            else pack.default_policy_outcome
        )
        explanation = top_decision.explanation
        if reviewer_required:
            explanation = (
                f"{explanation} Review required because evidence or confidence is limited."
            )
        return ClassificationTrace(
            classification_id=stable_id("cls", work_unit.work_unit_id, pack.basis),
            work_unit_id=work_unit.work_unit_id,
            policy_basis=pack.basis,
            work_category=work_category,
            policy_outcome=policy_outcome,
            cost_category=matched_rules[0]["decision"].get("cost_category", "ai_work")
            if matched_rules
            else "ai_work",
            direct_cost=work_unit.direct_cost,
            indirect_cost=work_unit.allocated_cost,
            blended_cost=work_unit.total_cost,
            confidence_score=confidence,
            evidence_score=evidence_score,
            evidence_strength=_evidence_strength(evidence_score),
            explanation=explanation,
            features_used=top_decision.features_used,
            reviewer_required=reviewer_required,
            reviewer_status="pending" if reviewer_required else "not_required",
            override_status="none",
            policy_hint=_policy_hint(work_category, policy_outcome),
            decisions=[top_decision, *decisions[1:]],
        )

    def _decision_from_rule(
        self,
        work_unit: WorkUnit,
        features: dict[str, Any],
        rule: dict[str, Any],
    ) -> PolicyDecision:
        decision = rule["decision"]
        explanation = rule.get("explanation", "Rule matched.")
        matched_features = {
            condition["feature"]: features.get(condition["feature"])
            for condition in rule.get("when", {}).get("all", [])
            + rule.get("when", {}).get("any", [])
        }
        return PolicyDecision(
            decision_id=stable_id("dec", work_unit.work_unit_id, rule["id"]),
            trace_id=work_unit.work_unit_id,
            rule_id=rule["id"],
            decision_type="work_category",
            value=decision["work_category"],
            confidence=float(decision.get("confidence", 0.75)),
            explanation=explanation,
            evidence_refs=[item.evidence_id for item in work_unit.evidence_bundle],
            requires_review=bool(decision.get("requires_review", False)),
            features_used=matched_features,
        )

    def _default_decision(
        self,
        work_unit: WorkUnit,
        pack: PolicyPack,
        features: dict[str, Any],
    ) -> PolicyDecision:
        return PolicyDecision(
            decision_id=stable_id("dec", work_unit.work_unit_id, "default", pack.basis),
            trace_id=work_unit.work_unit_id,
            rule_id="default",
            decision_type="work_category",
            value=pack.default_work_category,
            confidence=0.4,
            explanation="No policy rule matched; leaving classification conservative.",
            evidence_refs=[item.evidence_id for item in work_unit.evidence_bundle],
            requires_review=True,
            features_used=features,
        )
