from workledger.demo import coding_demo_events
from workledger.ingest.normalize import normalize_event
from workledger.rollup import RollupEngine


def test_rollup_groups_coding_work_into_two_work_units() -> None:
    spans = [normalize_event(event) for event in coding_demo_events()]
    work_units = RollupEngine().rollup(spans)
    assert len(work_units) == 3
    titles = {item.title for item in work_units}
    assert "Patch customer API timeout regression" in titles
    assert "Implement orchestration dashboard for customers" in titles
    assert "Automate release checklist workflow" in titles


def test_rollup_captures_supporting_lineage_and_outputs() -> None:
    spans = [normalize_event(event) for event in coding_demo_events()]
    work_unit = RollupEngine().rollup(spans)[0]
    assert work_unit.source_span_ids
    assert work_unit.evidence_bundle
    assert work_unit.output_artifact_refs
    assert work_unit.compression_ratio >= 1


def test_rollup_ids_and_evidence_are_deterministic() -> None:
    spans = [normalize_event(event) for event in coding_demo_events()]

    first = RollupEngine().rollup(spans)
    second = RollupEngine().rollup(spans)

    assert [item.work_unit_id for item in first] == [item.work_unit_id for item in second]
    assert [
        [evidence.evidence_id for evidence in item.evidence_bundle]
        for item in first
    ] == [
        [evidence.evidence_id for evidence in item.evidence_bundle]
        for item in second
    ]
    assert [
        [evidence.digest for evidence in item.evidence_bundle]
        for item in first
    ] == [
        [evidence.digest for evidence in item.evidence_bundle]
        for item in second
    ]
    assert all(
        evidence.digest
        for work_unit in first
        for evidence in work_unit.evidence_bundle
    )
