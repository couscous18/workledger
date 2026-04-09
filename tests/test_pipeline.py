from pathlib import Path

from workledger import WorkledgerConfig, WorkledgerPipeline
from workledger.demo import write_demo_file
from workledger.models import ObservationSpan, SourceKind, SpanKind
from workledger.review import apply_override


def test_end_to_end_pipeline(tmp_path: Path) -> None:
    config = WorkledgerConfig.from_project_dir(tmp_path / "project")
    pipeline = WorkledgerPipeline(config)
    input_path = write_demo_file("all", config.raw_events_dir / "all.jsonl")
    ingest = pipeline.ingest(input_path)
    work_units = pipeline.rollup()
    traces = pipeline.classify()
    artifacts = pipeline.report(include_economics=True)
    summary = pipeline.report_engine.summary(include_economics=True)
    pipeline.close()

    assert ingest.ingested >= 10
    assert len(work_units) >= 5
    assert len(traces) == len(work_units)
    assert any(artifact.report_kind == "html_summary" for artifact in artifacts)
    assert summary["totals"]["work_unit_count"] == len(work_units)
    assert "comparative_economics" in summary


def test_init_project_writes_builtin_policies(tmp_path: Path) -> None:
    config = WorkledgerConfig.from_project_dir(tmp_path / "project")
    pipeline = WorkledgerPipeline(config)
    pipeline.init_project()
    policy_names = {path.name for path in config.policies_dir.glob("*.yaml")}
    pipeline.close()

    assert "management_reporting_v1.yaml" in policy_names
    assert "software_capex_review_v1.yaml" in policy_names


def test_classify_is_idempotent_for_the_same_work_units(tmp_path: Path) -> None:
    config = WorkledgerConfig.from_project_dir(tmp_path / "project")
    pipeline = WorkledgerPipeline(config)
    input_path = write_demo_file("all", config.raw_events_dir / "all.jsonl")
    pipeline.ingest(input_path)
    work_units = pipeline.rollup()

    first = pipeline.classify()
    second = pipeline.classify()
    stored = pipeline.store.list_classifications()
    pipeline.close()

    assert len(first) == len(work_units)
    assert len(second) == len(work_units)
    assert len(stored) == len(work_units)
    assert {trace.classification_id for trace in first} == {
        trace.classification_id for trace in second
    }


def test_override_updates_explanation_hint_and_primary_decision(tmp_path: Path) -> None:
    config = WorkledgerConfig.from_project_dir(tmp_path / "project")
    pipeline = WorkledgerPipeline(config)
    input_path = write_demo_file("capex", config.raw_events_dir / "capex.jsonl")
    pipeline.ingest(input_path)
    pipeline.rollup()
    pipeline.classify(Path("software_capex_review_v1.yaml"))
    queue = pipeline.review_queue()

    override = apply_override(
        pipeline.store,
        classification_id=queue[0]["classification_id"],
        reviewer="controller",
        note="Confirmed as internal-use software.",
        work_category="internal_use_software",
        policy_outcome="capitalize_candidate",
    )
    updated = pipeline.store.get_classification(override.classification_id)
    pipeline.close()

    assert updated is not None
    assert updated.work_category == "internal_use_software"
    assert updated.policy_outcome == "capitalize_candidate"
    assert updated.policy_hint == "internal_use_software:capitalize_candidate:overridden"
    assert "Reviewer override by controller" in updated.explanation
    assert updated.decisions[0].value == "internal_use_software"


def test_observation_span_token_taxes_round_trip_in_storage(tmp_path: Path) -> None:
    config = WorkledgerConfig.from_project_dir(tmp_path / "project")
    pipeline = WorkledgerPipeline(config)
    span = ObservationSpan(
        source_kind=SourceKind.SDK,
        trace_id="trace_taxed",
        span_id="span_taxed",
        span_kind=SpanKind.LLM,
        name="Generate tax-aware completion",
        start_time="2026-04-06T12:00:00+00:00",
        end_time="2026-04-06T12:00:05+00:00",
        token_input=100,
        token_output=50,
        token_taxes=[
            {
                "name": "employment_style_token_tax",
                "jurisdiction": "US-NY",
                "rate": 0.07,
                "taxable_tokens": 150,
                "amount": 0.0012,
                "currency": "USD",
            }
        ],
        direct_cost=0.02,
    )

    pipeline.store.save_observation_spans([span])
    stored = pipeline.store.fetch_spans()
    pipeline.close()

    assert len(stored) == 1
    assert stored[0].token_taxes[0].jurisdiction == "US-NY"
    assert stored[0].token_taxes[0].included_in_direct_cost is False
