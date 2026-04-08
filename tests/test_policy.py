from pathlib import Path

from workledger.demo import coding_demo_events, marketing_demo_events, support_demo_events
from workledger.ingest.normalize import normalize_event
from workledger.policy import PolicyEngine, load_policy_pack
from workledger.rollup import RollupEngine


def _classify(events: list[dict[str, object]]) -> list[str]:
    work_units = RollupEngine().rollup([normalize_event(event) for event in events])
    traces, _ = PolicyEngine().classify(
        work_units, load_policy_pack(Path("policies/management_reporting_v1.yaml"))
    )
    return [trace.work_category for trace in traces]


def test_management_policy_classifies_coding_maintenance_and_product() -> None:
    functions = _classify(coding_demo_events())
    assert "maintenance_bugfix" in functions
    assert "external_product_development" in functions


def test_management_policy_classifies_marketing() -> None:
    functions = _classify(marketing_demo_events())
    assert functions == ["advertising_marketing"]


def test_management_policy_classifies_support() -> None:
    functions = _classify(support_demo_events())
    assert functions == ["support_service_delivery", "support_service_delivery"]
