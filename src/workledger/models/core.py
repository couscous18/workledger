from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field

from workledger.models.enums import (
    ActorKind,
    EvidenceStrength,
    ImportanceBand,
    PolicyOutcome,
    ReviewState,
    SourceKind,
    SpanKind,
    TrustState,
    WorkCategory,
)
from workledger.utils.ids import new_id


class WorkledgerModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, use_enum_values=True)


class EvidenceRef(WorkledgerModel):
    evidence_id: str = Field(default_factory=lambda: new_id("ev"))
    evidence_kind: str
    uri: str | None = None
    preview: str | None = None
    source_system: str
    digest: str | None = None
    sensitivity: str = "internal"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    attributes: dict[str, Any] = Field(default_factory=dict)


class TokenTax(WorkledgerModel):
    name: str
    jurisdiction: str
    rate: float = Field(ge=0.0)
    taxable_tokens: int | None = Field(default=None, ge=0)
    amount: float | None = Field(default=None, ge=0.0)
    currency: str | None = None
    included_in_direct_cost: bool = False


class ObservationSpan(WorkledgerModel):
    observation_id: str = Field(default_factory=lambda: new_id("obs"))
    source_kind: SourceKind
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    span_kind: SpanKind = SpanKind.OTHER
    name: str
    start_time: datetime
    end_time: datetime
    model_name: str | None = None
    provider: str | None = None
    tool_name: str | None = None
    token_input: int = 0
    token_output: int = 0
    token_taxes: list[TokenTax] = Field(default_factory=list)
    direct_cost: float = 0.0
    status: str = "ok"
    attributes: dict[str, Any] = Field(default_factory=dict)
    raw_payload_ref: str | None = None
    masked: bool = False
    redaction_applied: bool = False
    work_unit_key: str | None = None
    facets: dict[str, Any] = Field(default_factory=dict)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def duration_ms(self) -> int:
        return int((self.end_time - self.start_time).total_seconds() * 1000)


class WorkUnit(WorkledgerModel):
    work_unit_id: str = Field(default_factory=lambda: new_id("wu"))
    kind: str
    title: str
    summary: str
    objective: str | None = None
    actor: str | None = None
    actor_kind: ActorKind = ActorKind.SERVICE
    project: str | None = None
    team: str | None = None
    cost_center: str | None = None
    source_systems: list[str] = Field(default_factory=list)
    input_artifact_refs: list[str] = Field(default_factory=list)
    output_artifact_refs: list[str] = Field(default_factory=list)
    start_time: datetime
    end_time: datetime
    duration_ms: int
    review_state: ReviewState = ReviewState.UNREVIEWED
    trust_state: TrustState = TrustState.UNREVIEWED
    importance_score: float = 0.0
    importance_band: ImportanceBand = ImportanceBand.LOW
    direct_cost: float = 0.0
    allocated_cost: float = 0.0
    evidence_bundle: list[EvidenceRef] = Field(default_factory=list)
    lineage_refs: list[str] = Field(default_factory=list)
    source_span_ids: list[str] = Field(default_factory=list)
    compression_ratio: float = 1.0
    labels: list[str] = Field(default_factory=list)
    facets: dict[str, Any] = Field(default_factory=dict)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_cost(self) -> float:
        return round(self.direct_cost + self.allocated_cost, 6)


class PolicyDecision(WorkledgerModel):
    decision_id: str = Field(default_factory=lambda: new_id("dec"))
    trace_id: str
    rule_id: str
    model_id: str | None = None
    decision_type: str
    value: str
    confidence: float
    explanation: str
    evidence_refs: list[str] = Field(default_factory=list)
    competing_candidates: list[dict[str, Any]] = Field(default_factory=list)
    requires_review: bool = False
    features_used: dict[str, Any] = Field(default_factory=dict)


class ClassificationTrace(WorkledgerModel):
    classification_id: str = Field(default_factory=lambda: new_id("cls"))
    work_unit_id: str
    policy_basis: str
    work_category: WorkCategory = WorkCategory.UNKNOWN
    policy_outcome: PolicyOutcome = PolicyOutcome.REVIEW_REQUIRED
    cost_category: str = "ai_work"
    direct_cost: float = 0.0
    indirect_cost: float = 0.0
    blended_cost: float = 0.0
    confidence_score: float = 0.0
    evidence_score: float = 0.0
    evidence_strength: EvidenceStrength = EvidenceStrength.WEAK
    explanation: str
    features_used: dict[str, Any] = Field(default_factory=dict)
    reviewer_required: bool = False
    reviewer_status: str = "pending"
    override_status: str = "none"
    policy_hint: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    decisions: list[PolicyDecision] = Field(default_factory=list)


class PolicyPack(WorkledgerModel):
    policy_pack_id: str
    version: str
    basis: str
    title: str
    description: str
    default_work_category: WorkCategory = WorkCategory.UNKNOWN
    default_policy_outcome: PolicyOutcome = PolicyOutcome.REVIEW_REQUIRED
    rules: list[dict[str, Any]]


class PolicyRun(WorkledgerModel):
    policy_run_id: str = Field(default_factory=lambda: new_id("polrun"))
    policy_basis: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    trace_count: int = 0
    review_required_count: int = 0
    notes: str | None = None


class ReportArtifact(WorkledgerModel):
    report_id: str = Field(default_factory=lambda: new_id("rpt"))
    report_kind: str
    uri: str
    content_type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestError(WorkledgerModel):
    line: int | None = None
    error: str


class IngestResult(WorkledgerModel):
    ingested: int = 0
    skipped: int = 0
    errors: list[IngestError] = Field(default_factory=list)
    spans: list[ObservationSpan] = Field(default_factory=list, exclude=True)


class ReviewOverride(WorkledgerModel):
    override_id: str = Field(default_factory=lambda: new_id("ovr"))
    classification_id: str
    reviewer: str
    note: str
    work_category: WorkCategory | None = None
    policy_outcome: PolicyOutcome | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
