"""End-to-end pipeline: ingest, rollup, classify, report."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from workledger.benchmark import BenchmarkResult, run_benchmark
from workledger.config import WorkledgerConfig
from workledger.ingest.loader import ingest_path
from workledger.models import (
    ClassificationTrace,
    IngestError,
    IngestResult,
    ObservationSpan,
    PolicyPack,
    WorkUnit,
)
from workledger.policy import PolicyEngine, ensure_builtin_policies, load_policy_pack
from workledger.reporting import ReportEngine
from workledger.review import review_queue_items
from workledger.rollup import RollupConfig, RollupEngine
from workledger.storage import DuckDBStore

logger = logging.getLogger(__name__)


class WorkledgerPipeline:
    def __init__(self, config: WorkledgerConfig | None = None) -> None:
        self.config = config or WorkledgerConfig()
        self.config.ensure_dirs()
        policies_dir = self.config.policies_dir
        database_path = self.config.database_path
        assert policies_dir is not None
        assert database_path is not None
        ensure_builtin_policies(policies_dir)
        self.store = DuckDBStore(database_path)
        self.rollup_engine = RollupEngine(RollupConfig())
        self.policy_engine = PolicyEngine()
        self.report_engine = ReportEngine(self.store)

    def close(self) -> None:
        self.store.close()

    def init_project(self) -> WorkledgerConfig:
        self.config.ensure_dirs()
        return self.config

    def ingest(self, path: Path) -> IngestResult:
        result = ingest_path(path)
        if result.spans:
            self.store.save_observation_spans(result.spans)
        logger.info("Ingested %d spans from %s (skipped %d)", result.ingested, path, result.skipped)
        return result

    def ingest_payloads(self, payloads: list[dict[str, Any]]) -> IngestResult:
        raw_events_dir = self.config.raw_events_dir
        assert raw_events_dir is not None
        payload_path = raw_events_dir / "api-ingest.json"
        payload_path.write_text(json.dumps(payloads, indent=2), encoding="utf-8")
        spans: list[ObservationSpan] = []
        errors: list[IngestError] = []
        for index, payload in enumerate(payloads, start=1):
            try:
                spans.append(ObservationSpan.model_validate(payload))
            except ValueError as exc:
                errors.append(IngestError(line=index, error=str(exc)))
        if spans:
            self.store.save_observation_spans(spans)
        return IngestResult(
            ingested=len(spans),
            skipped=len(errors),
            errors=errors,
            spans=spans,
        )

    def rollup(self) -> list[WorkUnit]:
        spans = self.store.fetch_spans()
        work_units = self.rollup_engine.rollup(spans)
        self.store.save_work_units(work_units)
        logger.info("Rolled up %d spans into %d work units", len(spans), len(work_units))
        return work_units

    def classify(self, policy_path: Path | None = None) -> list[ClassificationTrace]:
        policy = self._load_policy(policy_path)
        work_units = self.store.list_work_units()
        traces, policy_run = self.policy_engine.classify(work_units, policy)
        self.store.save_classifications(traces)
        self.store.save_policy_run(policy_run)
        logger.info(
            "Classified %d work units (%d require review)",
            len(traces),
            policy_run.review_required_count,
        )
        return traces

    def report(self, *, include_economics: bool = False) -> list[Any]:
        reports_dir = self.config.reports_dir
        assert reports_dir is not None
        return self.report_engine.write_report_bundle(
            reports_dir,
            include_economics=include_economics,
        )

    def review_queue(self, limit: int | None = None) -> list[dict[str, Any]]:
        return review_queue_items(self.store, limit=limit)

    def explain(self, identifier: str) -> dict[str, Any]:
        work_unit = self.store.get_work_unit(identifier)
        if work_unit:
            return self._explain_work_unit(work_unit)
        trace = self.store.get_classification(identifier)
        if trace:
            work_unit = self.store.get_work_unit(trace.work_unit_id)
            if work_unit is None:
                return {
                    "work_unit": None,
                    "classifications": [trace.model_dump(mode="json")],
                    "source_spans": [],
                    "evidence_refs": [],
                    "lineage_refs": [],
                }
            return self._explain_work_unit(work_unit)
        raise ValueError(f"unknown work unit or classification: {identifier}")

    def _explain_work_unit(self, work_unit: WorkUnit) -> dict[str, Any]:
        related = [
            trace
            for trace in self.store.list_classifications()
            if trace.work_unit_id == work_unit.work_unit_id
        ]
        source_spans = self._compact_source_spans(work_unit.source_span_ids)
        return {
            "work_unit": work_unit.model_dump(mode="json"),
            "classifications": [trace.model_dump(mode="json") for trace in related],
            "source_spans": source_spans,
            "evidence_refs": [item.model_dump(mode="json") for item in work_unit.evidence_bundle],
            "lineage_refs": work_unit.lineage_refs,
        }

    def _compact_source_spans(self, source_span_ids: list[str]) -> list[dict[str, Any]]:
        spans_by_id = {span.span_id: span for span in self.store.fetch_spans()}
        compact_spans: list[dict[str, Any]] = []
        provenance_keys = ("actor", "project", "team", "cost_center", "labels")
        for span_id in source_span_ids:
            span = spans_by_id.get(span_id)
            if span is None:
                continue
            provenance = {
                key: span.attributes[key]
                for key in provenance_keys
                if key in span.attributes
            }
            compact_spans.append(
                {
                    "observation_id": span.observation_id,
                    "trace_id": span.trace_id,
                    "span_id": span.span_id,
                    "parent_span_id": span.parent_span_id,
                    "source_kind": span.source_kind,
                    "span_kind": span.span_kind,
                    "name": span.name,
                    "start_time": span.start_time.isoformat(),
                    "end_time": span.end_time.isoformat(),
                    "duration_ms": span.duration_ms,
                    "model_name": span.model_name,
                    "provider": span.provider,
                    "tool_name": span.tool_name,
                    "token_input": span.token_input,
                    "token_output": span.token_output,
                    "direct_cost": span.direct_cost,
                    "status": span.status,
                    "work_unit_key": span.work_unit_key,
                    "masked": span.masked,
                    "redaction_applied": span.redaction_applied,
                    "raw_payload_ref": span.raw_payload_ref,
                    "provenance": provenance,
                }
            )
        return compact_spans

    def export(self, table: str, fmt: str, destination: Path) -> Path:
        return self.store.export_table(table, destination, fmt)

    def benchmark(
        self, dataset_path: Path, policy_path: Path | None = None
    ) -> BenchmarkResult:
        return run_benchmark(dataset_path, policy_path=policy_path)

    def _load_policy(self, policy_path: Path | None) -> PolicyPack:
        if policy_path is None:
            policies_dir = self.config.policies_dir
            assert policies_dir is not None
            policy_path = policies_dir / "management_reporting_v1.yaml"
        return load_policy_pack(policy_path)
