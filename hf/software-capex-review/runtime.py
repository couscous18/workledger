# ruff: noqa: E402

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ensure_package(name: str, path: Path) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]  # type: ignore[attr-defined]
        sys.modules[name] = module
    return module


def _load_module(name: str, file_path: Path) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is not None and not (
        file_path.name == "__init__.py" and not getattr(module, "__file__", None)
    ):
        return module
    if module is not None:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name,
        file_path,
        submodule_search_locations=[str(file_path.parent)] if file_path.name == "__init__.py" else None,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _bootstrap_workledger_modules() -> None:
    root = repo_root()
    src_root = root / "src" / "workledger"
    _ensure_package("workledger", src_root)
    _ensure_package("workledger.models", src_root / "models")
    _ensure_package("workledger.utils", src_root / "utils")
    _ensure_package("workledger.storage", src_root / "storage")
    _ensure_package("workledger.ingest", src_root / "ingest")
    _ensure_package("workledger.rollup", src_root / "rollup")
    _ensure_package("workledger.policy", src_root / "policy")
    _ensure_package("workledger.reporting", src_root / "reporting")
    _load_module("workledger.utils.ids", src_root / "utils" / "ids.py")
    _load_module("workledger.models.enums", src_root / "models" / "enums.py")
    _load_module("workledger.models.core", src_root / "models" / "core.py")
    _load_module("workledger.models", src_root / "models" / "__init__.py")
    _load_module("workledger.config", root / "src" / "workledger" / "config.py")
    _load_module("workledger.ingest.normalize", src_root / "ingest" / "normalize.py")
    _load_module("workledger.ingest.loader", src_root / "ingest" / "loader.py")
    _load_module("workledger.storage.schema", src_root / "storage" / "schema.py")
    _load_module("workledger.storage.duckdb", src_root / "storage" / "duckdb.py")
    _load_module("workledger.storage", src_root / "storage" / "__init__.py")
    _load_module("workledger.rollup.features", src_root / "rollup" / "features.py")
    _load_module("workledger.rollup.engine", src_root / "rollup" / "engine.py")
    _load_module("workledger.rollup", src_root / "rollup" / "__init__.py")
    _load_module("workledger.policy.loader", src_root / "policy" / "loader.py")
    _load_module("workledger.policy.engine", src_root / "policy" / "engine.py")
    _load_module("workledger.policy", src_root / "policy" / "__init__.py")
    _load_module("workledger.reporting.engine", src_root / "reporting" / "engine.py")
    _load_module("workledger.reporting", src_root / "reporting" / "__init__.py")


_bootstrap_workledger_modules()

from workledger.config import WorkledgerConfig  # type: ignore[E402]
from workledger.ingest.normalize import normalize_event  # type: ignore[E402]
from workledger.policy import PolicyEngine, load_policy_pack  # type: ignore[E402]
from workledger.reporting import ReportEngine  # type: ignore[E402]
from workledger.rollup import RollupConfig, RollupEngine  # type: ignore[E402]
from workledger.storage import DuckDBStore  # type: ignore[E402]

DEFAULT_POLICY_PATH = repo_root() / "policies" / "management_reporting_v1.yaml"
DEFAULT_DATASET_PATH = (
    repo_root() / "hf" / "software-capex-review" / "dataset" / "software_capex_review_sample.jsonl"
)


def load_cases(path: Path | None = None) -> list[dict[str, Any]]:
    dataset_path = path or DEFAULT_DATASET_PATH
    cases: list[dict[str, Any]] = []
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        cases.append(json.loads(line))
    return cases


def load_payloads(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [dict(item) for item in payload]
    if isinstance(payload, dict) and "events" in payload:
        events = payload["events"]
        if isinstance(events, list):
            return [dict(item) for item in events]
    if isinstance(payload, dict):
        return [payload]
    raise ValueError(f"unsupported payload file: {path}")


def _case_key(work_unit: dict[str, Any]) -> str:
    for ref in work_unit.get("lineage_refs", []):
        if ref.startswith("group:"):
            return ref.removeprefix("group:")
    return work_unit["work_unit_id"]


def _review_need(trace: dict[str, Any]) -> float:
    confidence = float(trace.get("confidence_score", 0.0))
    evidence = float(trace.get("evidence_score", 0.0))
    reviewer_flag = 1.0 if trace.get("reviewer_required") else 0.0
    return reviewer_flag + max(0.0, 0.7 - confidence) + max(0.0, 0.45 - evidence)


def _rank_review_queue(
    traces: list[dict[str, Any]],
    work_units: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    work_units_by_id = {item["work_unit_id"]: item for item in work_units}
    queue: list[dict[str, Any]] = []
    for trace in traces:
        if not (
            trace.get("reviewer_required")
            or float(trace.get("confidence_score", 0.0)) < 0.7
            or float(trace.get("evidence_score", 0.0)) < 0.45
        ):
            continue
        work_unit = work_units_by_id[trace["work_unit_id"]]
        queue.append(
            {
                "work_unit_id": trace["work_unit_id"],
                "title": work_unit["title"],
                "work_category": trace["work_category"],
                "policy_outcome": trace["policy_outcome"],
                "blended_cost": trace["blended_cost"],
                "confidence_score": trace["confidence_score"],
                "evidence_score": trace["evidence_score"],
                "reviewer_required": trace["reviewer_required"],
                "override_status": trace["override_status"],
                "competing_candidates": trace.get("decisions", [{}])[0].get(
                    "competing_candidates", []
                ),
                "review_need": round(_review_need(trace), 3),
                "importance_score": float(work_unit["importance_score"]),
            }
        )
    queue.sort(
        key=lambda item: (
            -item["review_need"],
            -item["importance_score"],
            -float(item["blended_cost"]),
            float(item["confidence_score"]),
            item["work_unit_id"],
        )
    )
    return queue


def _summary_by_case(
    cases: list[dict[str, Any]],
    work_units: list[dict[str, Any]],
    traces: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    work_units_by_key = {_case_key(work_unit): work_unit for work_unit in work_units}
    traces_by_id = {trace["work_unit_id"]: trace for trace in traces}
    rows: list[dict[str, Any]] = []
    for case in cases:
        work_unit = work_units_by_key[case["case_id"]]
        trace = traces_by_id[work_unit["work_unit_id"]]
        expected = case["expected"]
        rows.append(
            {
                "case_id": case["case_id"],
                "title": work_unit["title"],
                "expected_work_category": expected.get(
                    "work_category", expected.get("function_class")
                ),
                "actual_work_category": trace["work_category"],
                "expected_policy_outcome": expected.get(
                    "policy_outcome", expected.get("treatment_candidate")
                ),
                "actual_policy_outcome": trace["policy_outcome"],
                "expected_reviewer_required": expected["reviewer_required"],
                "actual_reviewer_required": trace["reviewer_required"],
                "compression_ratio": work_unit["compression_ratio"],
                "confidence_score": trace["confidence_score"],
                "importance_score": work_unit["importance_score"],
            }
        )
    return rows


def evaluate_cases(
    cases: list[dict[str, Any]] | None = None,
    *,
    policy_path: Path | None = None,
) -> dict[str, Any]:
    case_rows = cases or load_cases()
    temp_root = Path(tempfile.mkdtemp(prefix="workledger-capex-"))
    config = WorkledgerConfig.from_project_dir(temp_root / "project")
    config.ensure_dirs()
    store = DuckDBStore(config.database_path)
    rollup_engine = RollupEngine(RollupConfig())
    policy_engine = PolicyEngine()
    try:
        payloads = [event for case in case_rows for event in case["events"]]
        spans = [normalize_event(payload) for payload in payloads]
        store.save_observation_spans(spans)
        work_units_models = rollup_engine.rollup(store.fetch_spans())
        store.save_work_units(work_units_models)
        policy = load_policy_pack(policy_path or DEFAULT_POLICY_PATH)
        traces_models, policy_run = policy_engine.classify(work_units_models, policy)
        store.save_classifications(traces_models)
        store.save_policy_run(policy_run)
        report_engine = ReportEngine(store)
        work_units = [item.model_dump(mode="json") for item in work_units_models]
        traces = [item.model_dump(mode="json") for item in traces_models]
        review_queue = _rank_review_queue(traces, work_units)
        summary = report_engine.summary()
    finally:
        store.close()
    per_case = _summary_by_case(case_rows, work_units, traces)
    return {
        "cases": case_rows,
        "work_units": work_units,
        "classifications": traces,
        "accounting_traces": traces,
        "review_queue": review_queue,
        "summary": summary,
        "per_case": per_case,
    }


def evaluate_payloads(
    payloads: list[dict[str, Any]],
    *,
    policy_path: Path | None = None,
) -> dict[str, Any]:
    temp_root = Path(tempfile.mkdtemp(prefix="workledger-capex-"))
    config = WorkledgerConfig.from_project_dir(temp_root / "project")
    config.ensure_dirs()
    store = DuckDBStore(config.database_path)
    rollup_engine = RollupEngine(RollupConfig())
    policy_engine = PolicyEngine()
    try:
        spans = [normalize_event(payload) for payload in payloads]
        store.save_observation_spans(spans)
        work_units_models = rollup_engine.rollup(store.fetch_spans())
        store.save_work_units(work_units_models)
        policy = load_policy_pack(policy_path or DEFAULT_POLICY_PATH)
        traces_models, policy_run = policy_engine.classify(work_units_models, policy)
        store.save_classifications(traces_models)
        store.save_policy_run(policy_run)
        report_engine = ReportEngine(store)
        work_units = [item.model_dump(mode="json") for item in work_units_models]
        traces = [item.model_dump(mode="json") for item in traces_models]
        review_queue = _rank_review_queue(traces, work_units)
        summary = report_engine.summary()
    finally:
        store.close()
    return {
        "payload_count": len(payloads),
        "work_units": work_units,
        "classifications": traces,
        "accounting_traces": traces,
        "review_queue": review_queue,
        "summary": summary,
    }


def benchmark_metrics(result: dict[str, Any]) -> dict[str, Any]:
    per_case = result.get("per_case", [])
    if not per_case:
        return {}
    total = len(per_case) or 1
    category_hits = sum(
        1 for row in per_case if row["expected_work_category"] == row["actual_work_category"]
    )
    treatment_hits = sum(
        1 for row in per_case if row["expected_policy_outcome"] == row["actual_policy_outcome"]
    )
    reviewer_hits = sum(
        1 for row in per_case if row["expected_reviewer_required"] == row["actual_reviewer_required"]
    )
    return {
        "cases": len(per_case),
        "work_category_accuracy": round(category_hits / total, 3),
        "policy_outcome_accuracy": round(treatment_hits / total, 3),
        "reviewer_accuracy": round(reviewer_hits / total, 3),
        "reviewer_required_rate": round(
            sum(1 for row in per_case if row["actual_reviewer_required"]) / total, 3
        ),
        "compression_average": round(
            sum(float(row["compression_ratio"]) for row in per_case) / total, 3
        ),
    }


def mismatches(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in result["per_case"]:
        mismatched: list[str] = []
        if row["expected_work_category"] != row["actual_work_category"]:
            mismatched.append("work_category")
        if row["expected_policy_outcome"] != row["actual_policy_outcome"]:
            mismatched.append("policy_outcome")
        if row["expected_reviewer_required"] != row["actual_reviewer_required"]:
            mismatched.append("reviewer_required")
        if mismatched:
            rows.append({**row, "mismatched_fields": mismatched})
    return rows


def _markdown_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    header = "| " + " | ".join(label for label, _ in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                str(row[key]) if key in row else ""
                for _, key in columns
            )
            + " |"
        )
    return "\n".join(lines)


def render_markdown(result: dict[str, Any]) -> str:
    metrics = benchmark_metrics(result)
    summary = result["summary"]["totals"]
    work_unit_rows = result.get("work_units", [])
    trace_rows = result.get("classifications", result.get("accounting_traces", []))
    work_units_by_id = {row["work_unit_id"]: row for row in work_unit_rows}
    trace_rows_for_table = [
        {**row, "title": work_units_by_id.get(row["work_unit_id"], {}).get("title", row["work_unit_id"])}
        for row in trace_rows
    ]
    lines = [
        "# Software capex review bundle",
        "",
        "## Metrics",
        "",
    ]
    if "cases" in metrics:
        lines.extend(
            [
                f"- cases: {metrics['cases']}",
                f"- work category accuracy: {metrics['work_category_accuracy']}",
                f"- policy outcome accuracy: {metrics['policy_outcome_accuracy']}",
                f"- reviewer accuracy: {metrics['reviewer_accuracy']}",
                f"- average compression ratio: {metrics['compression_average']}",
            ]
        )
    else:
        lines.append(f"- payloads: {result.get('payload_count', 0)}")
    lines.extend(["", "## Totals", ""])
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Work Units",
            "",
            _markdown_table(
                work_unit_rows,
                [
                    ("title", "title"),
                    ("kind", "kind"),
                    ("cost", "total_cost"),
                    ("compression", "compression_ratio"),
                ],
            ),
            "",
            "## Accounting Traces",
            "",
            _markdown_table(
                trace_rows_for_table,
                [
                    ("title", "title"),
                    ("work category", "work_category"),
                    ("policy outcome", "policy_outcome"),
                    ("cost", "blended_cost"),
                    ("confidence", "confidence_score"),
                    ("review", "reviewer_required"),
                ],
            ),
            "",
        ]
    )
    if "per_case" in result:
        lines.extend(["## Per-case results", ""])
        lines.append(
            _markdown_table(
                result["per_case"],
                [
                    ("case", "case_id"),
                    ("expected category", "expected_work_category"),
                    ("actual category", "actual_work_category"),
                    ("expected outcome", "expected_policy_outcome"),
                    ("actual outcome", "actual_policy_outcome"),
                    ("expected review", "expected_reviewer_required"),
                    ("actual review", "actual_reviewer_required"),
                    ("compression", "compression_ratio"),
                ],
            )
        )
        lines.extend(["", "## Review queue", ""])
    else:
        lines.extend(["## Review queue", ""])
    lines.append(
        _markdown_table(
            result["review_queue"],
            [
                ("title", "title"),
                ("work category", "work_category"),
                ("policy outcome", "policy_outcome"),
                ("cost", "blended_cost"),
                ("confidence", "confidence_score"),
                ("review need", "review_need"),
            ],
        )
    )
    return "\n".join(lines)
