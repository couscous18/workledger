from pathlib import Path

import duckdb

from workledger import WorkledgerConfig, WorkledgerPipeline
from workledger.demo import write_demo_file
from workledger.models import ObservationSpan, SourceKind, SpanKind
from workledger.review import apply_override
from workledger.storage import DuckDBStore


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


def test_observation_span_redaction_provenance_round_trip_in_storage(tmp_path: Path) -> None:
    config = WorkledgerConfig.from_project_dir(tmp_path / "project")
    pipeline = WorkledgerPipeline(config)
    span = ObservationSpan(
        source_kind=SourceKind.SDK,
        trace_id="trace_redacted",
        span_id="span_redacted",
        span_kind=SpanKind.LLM,
        name="Generate redacted completion",
        start_time="2026-04-06T12:00:00+00:00",
        end_time="2026-04-06T12:00:05+00:00",
        masked=True,
        redaction_applied=True,
    )

    pipeline.store.save_observation_spans([span])
    stored = pipeline.store.fetch_spans()
    pipeline.close()

    assert len(stored) == 1
    assert stored[0].masked is True
    assert stored[0].redaction_applied is True


def test_storage_bootstrap_adds_redaction_columns_to_existing_database(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.duckdb"
    connection = duckdb.connect(str(database_path))
    connection.execute(
        """
        create table observation_spans (
          observation_id varchar primary key,
          trace_id varchar not null,
          span_id varchar not null,
          parent_span_id varchar,
          source_kind varchar not null,
          span_kind varchar not null,
          name varchar not null,
          start_time timestamp not null,
          end_time timestamp not null,
          duration_ms bigint not null,
          model_name varchar,
          provider varchar,
          tool_name varchar,
          token_input bigint not null,
          token_output bigint not null,
          token_taxes_json json not null,
          direct_cost double not null,
          status varchar not null,
          work_unit_key varchar,
          attributes_json json not null,
          facets_json json not null,
          raw_payload_ref varchar
        )
        """
    )
    connection.close()

    store = DuckDBStore(database_path)
    columns = {
        row[0]
        for row in store.connection.execute(
            """
            select column_name
            from information_schema.columns
            where table_name = 'observation_spans'
            """
        ).fetchall()
    }
    store.close()

    assert "masked" in columns
    assert "redaction_applied" in columns


def test_explain_returns_attribution_graph_for_work_unit_and_classification(tmp_path: Path) -> None:
    config = WorkledgerConfig.from_project_dir(tmp_path / "project")
    pipeline = WorkledgerPipeline(config)
    input_path = write_demo_file("capex", config.raw_events_dir / "capex.jsonl")
    pipeline.ingest(input_path)
    work_units = pipeline.rollup()
    traces = pipeline.classify(config.policies_dir / "software_capex_review_v1.yaml")

    by_work_unit = pipeline.explain(work_units[0].work_unit_id)
    by_classification = pipeline.explain(traces[0].classification_id)
    pipeline.close()

    assert by_work_unit["work_unit"]["work_unit_id"] == work_units[0].work_unit_id
    assert by_work_unit["classifications"]
    assert by_work_unit["source_spans"]
    assert by_work_unit["evidence_refs"]
    assert by_work_unit["lineage_refs"] == work_units[0].lineage_refs
    assert "attributes" not in by_work_unit["source_spans"][0]
    assert {"masked", "redaction_applied"} <= set(by_work_unit["source_spans"][0])
    assert by_classification["work_unit"]["work_unit_id"] == traces[0].work_unit_id
    assert by_classification["source_spans"]
