from pathlib import Path

from workledger.benchmark import load_benchmark_suite, run_benchmark_suite
from workledger.ingest.loader import ingest_path
from workledger.policy import PolicyEngine, load_policy_pack
from workledger.rollup import RollupEngine


def test_software_capex_policy_classifies_benchmark_cases() -> None:
    suite = load_benchmark_suite(Path("benchmark-data/software_capex_review_v1"))
    policy = load_policy_pack(Path("policies/software_capex_review_v1.yaml"))

    seen = []
    for case in suite.cases:
        spans = ingest_path(case.input_path).spans
        work_units = RollupEngine().rollup(spans)
        traces, _ = PolicyEngine().classify(work_units, policy)
        assert len(traces) == 1
        trace = traces[0]
        seen.append((case.case_id, trace.work_category, trace.policy_outcome, trace.reviewer_required))

    assert seen == [
        ("maintenance_hotfix", "maintenance_bugfix", "maintenance_non_capitalizable", False),
        ("external_product_feature", "external_product_development", "capitalize_candidate", False),
        ("internal_tooling", "internal_use_software", "capitalize_candidate", True),
        ("ambiguous_review", "unknown", "review_required", True),
    ]


def test_software_capex_benchmark_case_results_match_policy() -> None:
    result = run_benchmark_suite(Path("benchmark-data/software_capex_review_v1"))
    assert {case.case_id for case in result.case_results} == {
        "maintenance_hotfix",
        "external_product_feature",
        "internal_tooling",
        "ambiguous_review",
    }
