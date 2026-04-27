from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypeVar

from workledger.models import (
    ClassificationTrace,
    EvidenceRef,
    ObservationSpan,
    PolicyDecision,
    PolicyRun,
    ReportArtifact,
    ReviewOverride,
    WorkUnit,
)
from workledger.storage.schema import SCHEMA_SQL

logger = logging.getLogger(__name__)

try:
    import duckdb
except ImportError as exc:  # pragma: no cover - import guard
    duckdb = None  # type: ignore[assignment]
    _DUCKDB_IMPORT_ERROR: ImportError | None = exc
else:  # pragma: no cover - small alias only
    _DUCKDB_IMPORT_ERROR = None

T = TypeVar("T")


def _require_duckdb() -> Any:
    if duckdb is None:
        raise RuntimeError("duckdb is required to use workledger storage") from _DUCKDB_IMPORT_ERROR
    return duckdb


class DuckDBStore:
    """Local analytical store for workledger objects."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        driver = _require_duckdb()
        self.connection = driver.connect(str(path))
        self.bootstrap()

    def bootstrap(self) -> None:
        for statement in SCHEMA_SQL:
            self.connection.execute(statement)
        self._ensure_json_column("observation_spans", "token_taxes_json", "[]")
        self._ensure_boolean_column("observation_spans", "masked", default=False)
        self._ensure_boolean_column("observation_spans", "redaction_applied", default=False)

    def close(self) -> None:
        self.connection.close()

    _KNOWN_TABLES = frozenset({
        "observation_spans",
        "work_units",
        "classification_traces",
        "policy_decisions",
        "policy_runs",
        "report_artifacts",
        "evidence_refs",
        "overrides",
    })

    def _validate_table_name(self, table: str) -> str:
        if table not in self._KNOWN_TABLES:
            raise ValueError(f"unknown table: {table}")
        return table

    def _ensure_json_column(self, table: str, column: str, default_json: str) -> None:
        self._validate_table_name(table)
        columns = {
            row[0]
            for row in self.connection.execute(
                """
                select column_name
                from information_schema.columns
                where table_name = ?
                """,
                [table],
            ).fetchall()
        }
        if column in columns:
            return
        safe_default = default_json.replace("'", "''")
        self.connection.execute(
            f"alter table {table} add column {column} json default '{safe_default}'"
        )

    def _ensure_boolean_column(self, table: str, column: str, *, default: bool) -> None:
        self._validate_table_name(table)
        columns = {
            row[0]
            for row in self.connection.execute(
                """
                select column_name
                from information_schema.columns
                where table_name = ?
                """,
                [table],
            ).fetchall()
        }
        if column in columns:
            return
        default_sql = "true" if default else "false"
        self.connection.execute(
            f"alter table {table} add column {column} boolean default {default_sql}"
        )

    def _replace_many(
        self, table: str, columns: list[str], rows: Iterable[tuple[Any, ...]]
    ) -> None:
        row_list = list(rows)
        if not row_list:
            return
        placeholders = ", ".join(["?"] * len(columns))
        self.connection.executemany(
            f"insert or replace into {table} ({', '.join(columns)}) values ({placeholders})",
            row_list,
        )

    def save_observation_spans(self, spans: list[ObservationSpan]) -> None:
        self._replace_many(
            "observation_spans",
            [
                "observation_id",
                "trace_id",
                "span_id",
                "parent_span_id",
                "source_kind",
                "span_kind",
                "name",
                "start_time",
                "end_time",
                "duration_ms",
                "model_name",
                "provider",
                "tool_name",
                "token_input",
                "token_output",
                "token_taxes_json",
                "direct_cost",
                "status",
                "work_unit_key",
                "masked",
                "redaction_applied",
                "attributes_json",
                "facets_json",
                "raw_payload_ref",
            ],
            [
                (
                    span.observation_id,
                    span.trace_id,
                    span.span_id,
                    span.parent_span_id,
                    span.source_kind,
                    span.span_kind,
                    span.name,
                    span.start_time,
                    span.end_time,
                    span.duration_ms,
                    span.model_name,
                    span.provider,
                    span.tool_name,
                    span.token_input,
                    span.token_output,
                    json.dumps([item.model_dump(mode="json") for item in span.token_taxes]),
                    span.direct_cost,
                    span.status,
                    span.work_unit_key,
                    span.masked,
                    span.redaction_applied,
                    json.dumps(span.attributes),
                    json.dumps(span.facets),
                    span.raw_payload_ref,
                )
                for span in spans
            ],
        )

    def save_evidence(self, evidence_refs: list[EvidenceRef]) -> None:
        self._replace_many(
            "evidence_refs",
            [
                "evidence_id",
                "evidence_kind",
                "uri",
                "preview",
                "source_system",
                "digest",
                "sensitivity",
                "timestamp",
                "attributes_json",
            ],
            [
                (
                    evidence.evidence_id,
                    evidence.evidence_kind,
                    evidence.uri,
                    evidence.preview,
                    evidence.source_system,
                    evidence.digest,
                    evidence.sensitivity,
                    evidence.timestamp,
                    json.dumps(evidence.attributes),
                )
                for evidence in evidence_refs
            ],
        )

    def save_work_units(self, work_units: list[WorkUnit]) -> None:
        evidence = [item for work_unit in work_units for item in work_unit.evidence_bundle]
        self.save_evidence(evidence)
        self._replace_many(
            "work_units",
            [
                "work_unit_id",
                "kind",
                "title",
                "summary",
                "objective",
                "actor",
                "actor_kind",
                "project",
                "team",
                "cost_center",
                "source_systems_json",
                "input_artifact_refs_json",
                "output_artifact_refs_json",
                "start_time",
                "end_time",
                "duration_ms",
                "review_state",
                "trust_state",
                "importance_score",
                "importance_band",
                "direct_cost",
                "allocated_cost",
                "evidence_bundle_json",
                "lineage_refs_json",
                "source_span_ids_json",
                "compression_ratio",
                "labels_json",
                "facets_json",
            ],
            [
                (
                    work_unit.work_unit_id,
                    work_unit.kind,
                    work_unit.title,
                    work_unit.summary,
                    work_unit.objective,
                    work_unit.actor,
                    work_unit.actor_kind,
                    work_unit.project,
                    work_unit.team,
                    work_unit.cost_center,
                    json.dumps(work_unit.source_systems),
                    json.dumps(work_unit.input_artifact_refs),
                    json.dumps(work_unit.output_artifact_refs),
                    work_unit.start_time,
                    work_unit.end_time,
                    work_unit.duration_ms,
                    work_unit.review_state,
                    work_unit.trust_state,
                    work_unit.importance_score,
                    work_unit.importance_band,
                    work_unit.direct_cost,
                    work_unit.allocated_cost,
                    json.dumps(
                        [item.model_dump(mode="json") for item in work_unit.evidence_bundle]
                    ),
                    json.dumps(work_unit.lineage_refs),
                    json.dumps(work_unit.source_span_ids),
                    work_unit.compression_ratio,
                    json.dumps(work_unit.labels),
                    json.dumps(work_unit.facets),
                )
                for work_unit in work_units
            ],
        )

    def save_classifications(self, traces: list[ClassificationTrace]) -> None:
        trace_ids = [trace.work_unit_id for trace in traces]
        if trace_ids:
            placeholders = ", ".join(["?"] * len(trace_ids))
            self.connection.execute(
                f"delete from policy_decisions where trace_id in ({placeholders})",
                trace_ids,
            )
        decisions = [decision for trace in traces for decision in trace.decisions]
        self.save_decisions(decisions)
        self._replace_many(
            "classification_traces",
            [
                "classification_id",
                "work_unit_id",
                "policy_basis",
                "work_category",
                "policy_outcome",
                "cost_category",
                "direct_cost",
                "indirect_cost",
                "blended_cost",
                "confidence_score",
                "evidence_score",
                "evidence_strength",
                "explanation",
                "features_used_json",
                "reviewer_required",
                "reviewer_status",
                "override_status",
                "policy_hint",
                "created_at",
                "decisions_json",
            ],
            [
                (
                    trace.classification_id,
                    trace.work_unit_id,
                    trace.policy_basis,
                    trace.work_category,
                    trace.policy_outcome,
                    trace.cost_category,
                    trace.direct_cost,
                    trace.indirect_cost,
                    trace.blended_cost,
                    trace.confidence_score,
                    trace.evidence_score,
                    trace.evidence_strength,
                    trace.explanation,
                    json.dumps(trace.features_used),
                    trace.reviewer_required,
                    trace.reviewer_status,
                    trace.override_status,
                    trace.policy_hint,
                    trace.created_at,
                    json.dumps([item.model_dump(mode="json") for item in trace.decisions]),
                )
                for trace in traces
            ],
        )

    def save_decisions(self, decisions: list[PolicyDecision]) -> None:
        self._replace_many(
            "policy_decisions",
            [
                "decision_id",
                "trace_id",
                "rule_id",
                "model_id",
                "decision_type",
                "value",
                "confidence",
                "explanation",
                "evidence_refs_json",
                "competing_candidates_json",
                "requires_review",
                "features_used_json",
            ],
            [
                (
                    decision.decision_id,
                    decision.trace_id,
                    decision.rule_id,
                    decision.model_id,
                    decision.decision_type,
                    decision.value,
                    decision.confidence,
                    decision.explanation,
                    json.dumps(decision.evidence_refs),
                    json.dumps(decision.competing_candidates),
                    decision.requires_review,
                    json.dumps(decision.features_used),
                )
                for decision in decisions
            ],
        )

    def save_policy_run(self, policy_run: PolicyRun) -> None:
        self._replace_many(
            "policy_runs",
            [
                "policy_run_id",
                "policy_basis",
                "started_at",
                "trace_count",
                "review_required_count",
                "notes",
            ],
            [
                (
                    policy_run.policy_run_id,
                    policy_run.policy_basis,
                    policy_run.started_at,
                    policy_run.trace_count,
                    policy_run.review_required_count,
                    policy_run.notes,
                )
            ],
        )

    def save_report(self, artifact: ReportArtifact) -> None:
        self._replace_many(
            "report_artifacts",
            ["report_id", "report_kind", "uri", "content_type", "created_at", "metadata_json"],
            [
                (
                    artifact.report_id,
                    artifact.report_kind,
                    artifact.uri,
                    artifact.content_type,
                    artifact.created_at,
                    json.dumps(artifact.metadata),
                )
            ],
        )

    def save_override(self, override: ReviewOverride) -> None:
        self._replace_many(
            "overrides",
            [
                "override_id",
                "classification_id",
                "reviewer",
                "note",
                "work_category",
                "policy_outcome",
                "created_at",
            ],
            [
                (
                    override.override_id,
                    override.classification_id,
                    override.reviewer,
                    override.note,
                    override.work_category,
                    override.policy_outcome,
                    override.created_at,
                )
            ],
        )

    def fetch_spans(self) -> list[ObservationSpan]:
        rows = self.connection.execute(
            """
            select
              observation_id, source_kind, trace_id, span_id, parent_span_id, span_kind, name, start_time,
              end_time, model_name, provider, tool_name, token_input, token_output, token_taxes_json,
              direct_cost, status, attributes_json, raw_payload_ref, work_unit_key, facets_json,
              masked, redaction_applied
            from observation_spans
            order by start_time
            """
        ).fetchall()
        return [
            ObservationSpan.model_validate(
                {
                    "observation_id": row[0],
                    "source_kind": row[1],
                    "trace_id": row[2],
                    "span_id": row[3],
                    "parent_span_id": row[4],
                    "span_kind": row[5],
                    "name": row[6],
                    "start_time": row[7],
                    "end_time": row[8],
                    "model_name": row[9],
                    "provider": row[10],
                    "tool_name": row[11],
                    "token_input": row[12],
                    "token_output": row[13],
                    "token_taxes": json.loads(row[14]) if row[14] else [],
                    "direct_cost": row[15],
                    "status": row[16],
                    "attributes": json.loads(row[17]),
                    "raw_payload_ref": row[18],
                    "work_unit_key": row[19],
                    "facets": json.loads(row[20]),
                    "masked": row[21],
                    "redaction_applied": row[22],
                }
            )
            for row in rows
        ]

    def list_work_units(self) -> list[WorkUnit]:
        rows = self.connection.execute(
            """
            select
              work_unit_id, kind, title, summary, objective, actor, actor_kind, project, team, cost_center,
              source_systems_json, input_artifact_refs_json, output_artifact_refs_json, start_time, end_time,
              duration_ms, review_state, trust_state, importance_score, importance_band, direct_cost,
              allocated_cost, evidence_bundle_json, lineage_refs_json, source_span_ids_json, compression_ratio,
              labels_json, facets_json
            from work_units
            order by start_time
            """
        ).fetchall()
        return [
            WorkUnit.model_validate(
                {
                    "work_unit_id": row[0],
                    "kind": row[1],
                    "title": row[2],
                    "summary": row[3],
                    "objective": row[4],
                    "actor": row[5],
                    "actor_kind": row[6],
                    "project": row[7],
                    "team": row[8],
                    "cost_center": row[9],
                    "source_systems": json.loads(row[10]),
                    "input_artifact_refs": json.loads(row[11]),
                    "output_artifact_refs": json.loads(row[12]),
                    "start_time": row[13],
                    "end_time": row[14],
                    "duration_ms": row[15],
                    "review_state": row[16],
                    "trust_state": row[17],
                    "importance_score": row[18],
                    "importance_band": row[19],
                    "direct_cost": row[20],
                    "allocated_cost": row[21],
                    "evidence_bundle": json.loads(row[22]),
                    "lineage_refs": json.loads(row[23]),
                    "source_span_ids": json.loads(row[24]),
                    "compression_ratio": row[25],
                    "labels": json.loads(row[26]),
                    "facets": json.loads(row[27]),
                }
            )
            for row in rows
        ]

    def get_work_unit(self, work_unit_id: str) -> WorkUnit | None:
        rows = self.connection.execute(
            """
            select
              work_unit_id, kind, title, summary, objective, actor, actor_kind, project, team, cost_center,
              source_systems_json, input_artifact_refs_json, output_artifact_refs_json, start_time, end_time,
              duration_ms, review_state, trust_state, importance_score, importance_band, direct_cost,
              allocated_cost, evidence_bundle_json, lineage_refs_json, source_span_ids_json, compression_ratio,
              labels_json, facets_json
            from work_units
            where work_unit_id = ?
            """,
            [work_unit_id],
        ).fetchall()
        if not rows:
            return None
        row = rows[0]
        return WorkUnit.model_validate(
            {
                "work_unit_id": row[0],
                "kind": row[1],
                "title": row[2],
                "summary": row[3],
                "objective": row[4],
                "actor": row[5],
                "actor_kind": row[6],
                "project": row[7],
                "team": row[8],
                "cost_center": row[9],
                "source_systems": json.loads(row[10]),
                "input_artifact_refs": json.loads(row[11]),
                "output_artifact_refs": json.loads(row[12]),
                "start_time": row[13],
                "end_time": row[14],
                "duration_ms": row[15],
                "review_state": row[16],
                "trust_state": row[17],
                "importance_score": row[18],
                "importance_band": row[19],
                "direct_cost": row[20],
                "allocated_cost": row[21],
                "evidence_bundle": json.loads(row[22]),
                "lineage_refs": json.loads(row[23]),
                "source_span_ids": json.loads(row[24]),
                "compression_ratio": row[25],
                "labels": json.loads(row[26]),
                "facets": json.loads(row[27]),
            }
        )

    def list_classifications(self) -> list[ClassificationTrace]:
        rows = self.connection.execute(
            """
            select
              classification_id, work_unit_id, policy_basis, work_category, policy_outcome, cost_category,
              direct_cost, indirect_cost, blended_cost, confidence_score, evidence_score, evidence_strength,
              explanation, features_used_json, reviewer_required, reviewer_status, override_status, policy_hint,
              created_at, decisions_json
            from classification_traces
            order by created_at desc
            """
        ).fetchall()
        return [
            ClassificationTrace.model_validate(
                {
                    "classification_id": row[0],
                    "work_unit_id": row[1],
                    "policy_basis": row[2],
                    "work_category": row[3],
                    "policy_outcome": row[4],
                    "cost_category": row[5],
                    "direct_cost": row[6],
                    "indirect_cost": row[7],
                    "blended_cost": row[8],
                    "confidence_score": row[9],
                    "evidence_score": row[10],
                    "evidence_strength": row[11],
                    "explanation": row[12],
                    "features_used": json.loads(row[13]),
                    "reviewer_required": row[14],
                    "reviewer_status": row[15],
                    "override_status": row[16],
                    "policy_hint": row[17],
                    "created_at": row[18],
                    "decisions": json.loads(row[19]),
                }
            )
            for row in rows
        ]

    def get_classification(self, classification_id: str) -> ClassificationTrace | None:
        rows = self.connection.execute(
            """
            select
              classification_id, work_unit_id, policy_basis, work_category, policy_outcome, cost_category,
              direct_cost, indirect_cost, blended_cost, confidence_score, evidence_score, evidence_strength,
              explanation, features_used_json, reviewer_required, reviewer_status, override_status, policy_hint,
              created_at, decisions_json
            from classification_traces
            where classification_id = ?
            """,
            [classification_id],
        ).fetchall()
        if not rows:
            return None
        row = rows[0]
        return ClassificationTrace.model_validate(
            {
                "classification_id": row[0],
                "work_unit_id": row[1],
                "policy_basis": row[2],
                "work_category": row[3],
                "policy_outcome": row[4],
                "cost_category": row[5],
                "direct_cost": row[6],
                "indirect_cost": row[7],
                "blended_cost": row[8],
                "confidence_score": row[9],
                "evidence_score": row[10],
                "evidence_strength": row[11],
                "explanation": row[12],
                "features_used": json.loads(row[13]),
                "reviewer_required": row[14],
                "reviewer_status": row[15],
                "override_status": row[16],
                "policy_hint": row[17],
                "created_at": row[18],
                "decisions": json.loads(row[19]),
            }
        )

    def list_decisions(self) -> list[PolicyDecision]:
        rows = self.connection.execute(
            """
            select
              decision_id, trace_id, rule_id, model_id, decision_type, value, confidence, explanation,
              evidence_refs_json, competing_candidates_json, requires_review, features_used_json
            from policy_decisions
            order by confidence desc
            """
        ).fetchall()
        return [
            PolicyDecision.model_validate(
                {
                    "decision_id": row[0],
                    "trace_id": row[1],
                    "rule_id": row[2],
                    "model_id": row[3],
                    "decision_type": row[4],
                    "value": row[5],
                    "confidence": row[6],
                    "explanation": row[7],
                    "evidence_refs": json.loads(row[8]),
                    "competing_candidates": json.loads(row[9]),
                    "requires_review": row[10],
                    "features_used": json.loads(row[11]),
                }
            )
            for row in rows
        ]

    def list_reports(self) -> list[ReportArtifact]:
        rows = self.connection.execute(
            """
            select report_id, report_kind, uri, content_type, created_at, metadata_json
            from report_artifacts
            order by created_at desc
            """
        ).fetchall()
        return [
            ReportArtifact.model_validate(
                {
                    "report_id": row[0],
                    "report_kind": row[1],
                    "uri": row[2],
                    "content_type": row[3],
                    "created_at": row[4],
                    "metadata": json.loads(row[5]),
                }
            )
            for row in rows
        ]

    def list_overrides(self) -> list[ReviewOverride]:
        rows = self.connection.execute(
            """
            select override_id, classification_id, reviewer, note, work_category, policy_outcome, created_at
            from overrides
            order by created_at desc
            """
        ).fetchall()
        return [
            ReviewOverride.model_validate(
                {
                    "override_id": row[0],
                    "classification_id": row[1],
                    "reviewer": row[2],
                    "note": row[3],
                    "work_category": row[4],
                    "policy_outcome": row[5],
                    "created_at": row[6],
                }
            )
            for row in rows
        ]

    def export_table(self, table: str, destination: Path, fmt: str) -> Path:
        self._validate_table_name(table)
        destination.parent.mkdir(parents=True, exist_ok=True)
        safe_dest = str(destination).replace("'", "''")
        if fmt == "parquet":
            self.connection.execute(f"COPY {table} TO '{safe_dest}' (FORMAT PARQUET)")
        elif fmt == "csv":
            self.connection.execute(f"COPY {table} TO '{safe_dest}' (HEADER, DELIMITER ',')")
        elif fmt == "json":
            rows = self.connection.execute(f"select * from {table}").fetchall()
            columns = [column[0] for column in self.connection.description]
            payload = [dict(zip(columns, row, strict=False)) for row in rows]
            destination.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        else:
            raise ValueError(f"unsupported export format: {fmt}")
        return destination
