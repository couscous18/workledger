"""Benchmark evaluation engine for measuring policy pack accuracy."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from workledger.ingest.loader import ingest_path
from workledger.models import ClassificationTrace, PolicyPack, WorkUnit
from workledger.policy import PolicyEngine, load_policy_pack
from workledger.rollup import RollupEngine
from workledger.rollup.features import SUPPRESSED_SPAN_KINDS


def _resolve_path(base_dir: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


def _safe_divide(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 3)


@dataclass(slots=True)
class BenchmarkCaseSpec:
    case_id: str
    input_path: Path
    expected_work_category: str
    expected_policy_outcome: str
    expected_reviewer_required: bool

    @classmethod
    def from_mapping(cls, base_dir: Path, payload: dict[str, Any]) -> BenchmarkCaseSpec:
        expected_work_category = payload.get(
            "expected_work_category", payload.get("expected_function_class")
        )
        expected_policy_outcome = payload.get(
            "expected_policy_outcome", payload.get("expected_treatment_candidate")
        )
        return cls(
            case_id=str(payload["case_id"]),
            input_path=_resolve_path(base_dir, payload["input_path"]),
            expected_work_category=str(expected_work_category),
            expected_policy_outcome=str(expected_policy_outcome),
            expected_reviewer_required=bool(payload["expected_reviewer_required"]),
        )


@dataclass(slots=True)
class BenchmarkSuiteSpec:
    benchmark_id: str
    policy_path: Path
    cases: list[BenchmarkCaseSpec]

    @classmethod
    def from_manifest(cls, manifest_path: Path) -> BenchmarkSuiteSpec:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        base_dir = manifest_path.parent
        return cls(
            benchmark_id=str(payload["benchmark_id"]),
            policy_path=_resolve_path(base_dir, payload["policy_path"]),
            cases=[
                BenchmarkCaseSpec.from_mapping(base_dir, case_payload)
                for case_payload in payload["cases"]
            ],
        )


@dataclass(slots=True)
class BenchmarkCaseResult:
    case_id: str
    title: str
    work_unit_id: str
    source_span_count: int
    material_span_count: int
    compression_ratio: float
    expected_work_category: str
    actual_work_category: str
    expected_policy_outcome: str
    actual_policy_outcome: str
    expected_reviewer_required: bool
    actual_reviewer_required: bool
    confidence_score: float
    blended_cost: float
    mismatches: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "title": self.title,
            "work_unit_id": self.work_unit_id,
            "source_span_count": self.source_span_count,
            "material_span_count": self.material_span_count,
            "compression_ratio": self.compression_ratio,
            "expected_work_category": self.expected_work_category,
            "actual_work_category": self.actual_work_category,
            "expected_policy_outcome": self.expected_policy_outcome,
            "actual_policy_outcome": self.actual_policy_outcome,
            "expected_reviewer_required": self.expected_reviewer_required,
            "actual_reviewer_required": self.actual_reviewer_required,
            "confidence_score": self.confidence_score,
            "blended_cost": self.blended_cost,
            "mismatches": self.mismatches,
        }


@dataclass(slots=True)
class BenchmarkResult:
    benchmark_id: str
    policy_basis: str
    total_cases: int
    class_accuracy: float
    treatment_accuracy: float
    reviewer_precision: float
    reviewer_recall: float
    average_compression_ratio: float
    work_category_confusion: list[dict[str, Any]]
    treatment_confusion: list[dict[str, Any]]
    case_results: list[BenchmarkCaseResult]

    @property
    def mismatches(self) -> list[dict[str, Any]]:
        return [case.to_dict() for case in self.case_results if case.mismatches]

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "policy_basis": self.policy_basis,
            "total_cases": self.total_cases,
            "class_accuracy": self.class_accuracy,
            "treatment_accuracy": self.treatment_accuracy,
            "reviewer_precision": self.reviewer_precision,
            "reviewer_recall": self.reviewer_recall,
            "average_compression_ratio": self.average_compression_ratio,
            "work_category_confusion": self.work_category_confusion,
            "treatment_confusion": self.treatment_confusion,
            "case_results": [case.to_dict() for case in self.case_results],
            "mismatches": self.mismatches,
        }


def load_benchmark_suite(path: Path) -> BenchmarkSuiteSpec:
    manifest_path = path / "manifest.json" if path.is_dir() else path
    return BenchmarkSuiteSpec.from_manifest(manifest_path)


def _evaluate_trace(
    case: BenchmarkCaseSpec,
    work_unit: WorkUnit,
    trace: ClassificationTrace,
    material_span_count: int,
) -> BenchmarkCaseResult:
    mismatches: list[str] = []
    if trace.work_category != case.expected_work_category:
        mismatches.append("work_category")
    if trace.policy_outcome != case.expected_policy_outcome:
        mismatches.append("policy_outcome")
    if trace.reviewer_required != case.expected_reviewer_required:
        mismatches.append("reviewer_required")
    return BenchmarkCaseResult(
        case_id=case.case_id,
        title=work_unit.title,
        work_unit_id=work_unit.work_unit_id,
        source_span_count=len(work_unit.source_span_ids),
        material_span_count=material_span_count,
        compression_ratio=work_unit.compression_ratio,
        expected_work_category=case.expected_work_category,
        actual_work_category=str(trace.work_category),
        expected_policy_outcome=case.expected_policy_outcome,
        actual_policy_outcome=str(trace.policy_outcome),
        expected_reviewer_required=case.expected_reviewer_required,
        actual_reviewer_required=trace.reviewer_required,
        confidence_score=trace.confidence_score,
        blended_cost=trace.blended_cost,
        mismatches=mismatches,
    )


def evaluate_case(
    case: BenchmarkCaseSpec, policy_pack: PolicyPack, rollup_engine: RollupEngine | None = None
) -> BenchmarkCaseResult:
    spans = ingest_path(case.input_path).spans
    work_units = (rollup_engine or RollupEngine()).rollup(spans)
    if len(work_units) != 1:
        raise ValueError(
            f"benchmark case {case.case_id} produced {len(work_units)} work units; expected 1"
        )
    traces, _ = PolicyEngine().classify(work_units, policy_pack)
    if len(traces) != 1:
        raise ValueError(
            f"benchmark case {case.case_id} produced {len(traces)} classification traces; expected 1"
        )
    material_span_count = sum(
        1 for span in spans if span.span_kind not in SUPPRESSED_SPAN_KINDS
    )
    return _evaluate_trace(case, work_units[0], traces[0], material_span_count)


def _confusion_rows(
    case_results: list[BenchmarkCaseResult], expected_key: str, actual_key: str
) -> list[dict[str, Any]]:
    counts = Counter(
        (
            getattr(case, expected_key),
            getattr(case, actual_key),
        )
        for case in case_results
    )
    return [
        {"expected": expected, "actual": actual, "count": count}
        for (expected, actual), count in sorted(counts.items())
    ]


def run_benchmark_suite(
    suite_or_path: BenchmarkSuiteSpec | Path, policy_path: Path | None = None
) -> BenchmarkResult:
    suite = (
        suite_or_path
        if isinstance(suite_or_path, BenchmarkSuiteSpec)
        else load_benchmark_suite(suite_or_path)
    )
    pack = load_policy_pack(policy_path or suite.policy_path)
    case_results = [evaluate_case(case, pack) for case in suite.cases]
    total_cases = len(case_results)
    class_matches = sum(
        1 for case in case_results if case.expected_work_category == case.actual_work_category
    )
    treatment_matches = sum(
        1
        for case in case_results
        if case.expected_policy_outcome == case.actual_policy_outcome
    )
    reviewer_tp = sum(
        1
        for case in case_results
        if case.expected_reviewer_required and case.actual_reviewer_required
    )
    reviewer_fp = sum(
        1
        for case in case_results
        if not case.expected_reviewer_required and case.actual_reviewer_required
    )
    reviewer_fn = sum(
        1
        for case in case_results
        if case.expected_reviewer_required and not case.actual_reviewer_required
    )
    return BenchmarkResult(
        benchmark_id=suite.benchmark_id,
        policy_basis=pack.basis,
        total_cases=total_cases,
        class_accuracy=_safe_divide(class_matches, total_cases),
        treatment_accuracy=_safe_divide(treatment_matches, total_cases),
        reviewer_precision=_safe_divide(reviewer_tp, reviewer_tp + reviewer_fp),
        reviewer_recall=_safe_divide(reviewer_tp, reviewer_tp + reviewer_fn),
        average_compression_ratio=round(
            sum(case.compression_ratio for case in case_results) / total_cases, 3
        )
        if total_cases
        else 1.0,
        work_category_confusion=_confusion_rows(
            case_results, "expected_work_category", "actual_work_category"
        ),
        treatment_confusion=_confusion_rows(
            case_results, "expected_policy_outcome", "actual_policy_outcome"
        ),
        case_results=case_results,
    )


def run_benchmark(
    suite_or_path: BenchmarkSuiteSpec | Path, policy_path: Path | None = None
) -> BenchmarkResult:
    return run_benchmark_suite(suite_or_path, policy_path=policy_path)


def render_benchmark_markdown(result: BenchmarkResult) -> str:
    lines = [
        f"# Benchmark: {result.benchmark_id}",
        "",
        "## Summary",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| policy basis | {result.policy_basis} |",
        f"| total cases | {result.total_cases} |",
        f"| work category accuracy | {result.class_accuracy:.3f} |",
        f"| policy outcome accuracy | {result.treatment_accuracy:.3f} |",
        f"| reviewer precision | {result.reviewer_precision:.3f} |",
        f"| reviewer recall | {result.reviewer_recall:.3f} |",
        f"| average compression ratio | {result.average_compression_ratio:.3f} |",
        "",
        "## Work Category Confusion",
        "",
        "| expected | actual | count |",
        "| --- | --- | ---: |",
    ]
    for row in result.work_category_confusion:
        lines.append(f"| {row['expected']} | {row['actual']} | {row['count']} |")
    lines.extend(
        [
            "",
            "## Policy Outcome Confusion",
            "",
            "| expected | actual | count |",
            "| --- | --- | ---: |",
        ]
    )
    for row in result.treatment_confusion:
        lines.append(f"| {row['expected']} | {row['actual']} | {row['count']} |")
    lines.extend(
        [
            "",
            "## Mismatches",
            "",
        ]
    )
    if result.mismatches:
        for case in result.mismatches:
            lines.append(
                f"- {case['case_id']}: {', '.join(case['mismatches'])} "
                f"(expected {case['expected_work_category']} / {case['expected_policy_outcome']} / "
                f"{case['expected_reviewer_required']}, got {case['actual_work_category']} / "
                f"{case['actual_policy_outcome']} / {case['actual_reviewer_required']})"
            )
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def write_benchmark_report(
    result: BenchmarkResult, destination: Path, fmt: str = "json"
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        destination.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    elif fmt == "markdown":
        destination.write_text(render_benchmark_markdown(result), encoding="utf-8")
    else:
        raise ValueError(f"unsupported benchmark format: {fmt}")
    return destination
