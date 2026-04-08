from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from workledger.models import EvidenceRef, ObservationSpan, SpanKind, WorkUnit
from workledger.rollup.features import (
    SUPPRESSED_SPAN_KINDS,
    importance_band,
    importance_score,
    infer_actor_kind,
    infer_artifacts,
    infer_kind,
    infer_objective,
    infer_review_state,
    infer_summary,
    infer_title,
    infer_trust_state,
    merge_facets,
    summarize_sources,
)


@dataclass(slots=True)
class RollupRule:
    name: str
    match_attribute: str
    group_by_attribute: str


@dataclass(slots=True)
class RollupConfig:
    grouping_keys: list[str] = field(
        default_factory=lambda: [
            "work_unit_key",
            "work_unit_id",
            "task_id",
            "issue_id",
            "ticket_id",
            "campaign_id",
            "session_id",
        ]
    )
    rules: list[RollupRule] = field(default_factory=list)
    allocated_cost_multiplier: float = 0.15


class RollupEngine:
    def __init__(self, config: RollupConfig | None = None) -> None:
        self.config = config or RollupConfig()

    def group_key(self, span: ObservationSpan) -> str:
        if span.work_unit_key:
            return span.work_unit_key
        for rule in self.config.rules:
            if span.attributes.get(rule.match_attribute):
                candidate = span.attributes.get(rule.group_by_attribute)
                if candidate:
                    return str(candidate)
        for key in self.config.grouping_keys:
            if key == "work_unit_key":
                continue
            candidate = span.attributes.get(key)
            if candidate:
                return str(candidate)
        return span.trace_id

    def rollup(self, spans: list[ObservationSpan]) -> list[WorkUnit]:
        grouped: dict[str, list[ObservationSpan]] = defaultdict(list)
        for span in sorted(spans, key=lambda item: item.start_time):
            grouped[self.group_key(span)].append(span)
        return [self._build_work_unit(group, span_group) for group, span_group in grouped.items()]

    def _build_work_unit(self, group_key: str, spans: list[ObservationSpan]) -> WorkUnit:
        sorted_spans = sorted(spans, key=lambda item: item.start_time)
        start_time = sorted_spans[0].start_time
        end_time = max(span.end_time for span in sorted_spans)
        review_state = infer_review_state(sorted_spans)
        direct_cost = round(sum(span.direct_cost for span in sorted_spans), 6)
        title = infer_title(sorted_spans)
        summary = infer_summary(sorted_spans)
        outputs = infer_artifacts(sorted_spans, "output_artifacts")
        inputs = infer_artifacts(sorted_spans, "input_artifacts")
        score = importance_score(sorted_spans)
        evidence = self._build_evidence(sorted_spans, outputs)
        material_spans = [
            span for span in sorted_spans if span.span_kind not in SUPPRESSED_SPAN_KINDS
        ]
        compression_ratio = round(len(sorted_spans) / max(1, len(material_spans)), 2)
        labels = sorted(
            {
                value
                for span in sorted_spans
                for value in span.attributes.get("labels", [])
                if isinstance(value, str)
            }
        )
        return WorkUnit(
            kind=infer_kind(sorted_spans),
            title=title,
            summary=summary,
            objective=infer_objective(sorted_spans),
            actor=sorted_spans[0].attributes.get("actor"),
            actor_kind=infer_actor_kind(sorted_spans),
            project=sorted_spans[0].attributes.get("project"),
            team=sorted_spans[0].attributes.get("team"),
            cost_center=sorted_spans[0].attributes.get("cost_center"),
            source_systems=summarize_sources(sorted_spans),
            input_artifact_refs=inputs,
            output_artifact_refs=outputs,
            start_time=start_time,
            end_time=end_time,
            duration_ms=int((end_time - start_time).total_seconds() * 1000),
            review_state=review_state,
            trust_state=infer_trust_state(sorted_spans, review_state),
            importance_score=score,
            importance_band=importance_band(score),
            direct_cost=direct_cost,
            allocated_cost=round(direct_cost * self.config.allocated_cost_multiplier, 6),
            evidence_bundle=evidence,
            lineage_refs=[f"trace:{sorted_spans[0].trace_id}", f"group:{group_key}"],
            source_span_ids=[span.span_id for span in sorted_spans],
            compression_ratio=compression_ratio,
            labels=labels,
            facets=merge_facets(sorted_spans),
        )

    def _build_evidence(
        self, spans: list[ObservationSpan], outputs: list[str]
    ) -> list[EvidenceRef]:
        evidence: list[EvidenceRef] = [
            EvidenceRef(
                evidence_kind="trace_group",
                preview=f"{len(spans)} spans grouped into one work unit",
                source_system="workledger",
                attributes={"span_ids": [span.span_id for span in spans]},
            )
        ]
        if outputs:
            for output in outputs:
                evidence.append(
                    EvidenceRef(
                        evidence_kind="output_artifact",
                        uri=output,
                        preview=output,
                        source_system="trace",
                    )
                )
        if any(span.span_kind == SpanKind.REVIEW for span in spans):
            evidence.append(
                EvidenceRef(
                    evidence_kind="human_review",
                    preview="Human review span observed",
                    source_system="trace",
                )
            )
        return evidence
