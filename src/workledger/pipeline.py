"""End-to-end pipeline: ingest, rollup, classify, report."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from workledger.adapters import (
    HuggingFaceIngestResult,
    adapt_huggingface_dataset,
)
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

    def ingest_huggingface(
        self,
        dataset_id: str,
        *,
        adapter_name: str = "auto",
        split: str = "train",
        limit: int | None = None,
        seed: int = 7,
    ) -> HuggingFaceIngestResult:
        raw_events_dir = self.config.raw_events_dir
        assert raw_events_dir is not None
        bundle = adapt_huggingface_dataset(
            dataset_id=dataset_id,
            split=split,
            adapter_name=adapter_name,
            limit=limit,
            seed=seed,
        )
        raw_path = raw_events_dir / f"{dataset_id.replace('/', '-')}-{split}.jsonl"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        payload = "\n".join(json.dumps(row, sort_keys=True, default=str) for row in bundle.rows)
        raw_path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")
        ingest_result = IngestResult(
            ingested=len(bundle.spans),
            skipped=0,
            errors=[],
            spans=bundle.spans,
        )
        if bundle.spans:
            self.store.save_observation_spans(bundle.spans)
        logger.info(
            "Ingested %d spans from Hugging Face dataset %s[%s] using %s",
            len(bundle.spans),
            dataset_id,
            split,
            bundle.adapter_name,
        )
        return HuggingFaceIngestResult(
            dataset_id=dataset_id,
            split=split,
            adapter_name=bundle.adapter_name,
            row_count=len(bundle.rows),
            raw_path=raw_path,
            ingest=ingest_result,
        )

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
            related = [
                trace
                for trace in self.store.list_classifications()
                if trace.work_unit_id == work_unit.work_unit_id
            ]
            return {
                "work_unit": work_unit.model_dump(mode="json"),
                "classifications": [trace.model_dump(mode="json") for trace in related],
            }
        trace = self.store.get_classification(identifier)
        if trace:
            return {"classification": trace.model_dump(mode="json")}
        raise ValueError(f"unknown work unit or classification: {identifier}")

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
