SCHEMA_SQL = [
    """
    create table if not exists observation_spans (
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
      masked boolean not null default false,
      redaction_applied boolean not null default false,
      attributes_json json not null,
      facets_json json not null,
      raw_payload_ref varchar
    )
    """,
    """
    create table if not exists evidence_refs (
      evidence_id varchar primary key,
      evidence_kind varchar not null,
      uri varchar,
      preview varchar,
      source_system varchar not null,
      digest varchar,
      sensitivity varchar not null,
      timestamp timestamp not null,
      attributes_json json not null
    )
    """,
    """
    create table if not exists work_units (
      work_unit_id varchar primary key,
      kind varchar not null,
      title varchar not null,
      summary varchar not null,
      objective varchar,
      actor varchar,
      actor_kind varchar not null,
      project varchar,
      team varchar,
      cost_center varchar,
      source_systems_json json not null,
      input_artifact_refs_json json not null,
      output_artifact_refs_json json not null,
      start_time timestamp not null,
      end_time timestamp not null,
      duration_ms bigint not null,
      review_state varchar not null,
      trust_state varchar not null,
      importance_score double not null,
      importance_band varchar not null,
      direct_cost double not null,
      allocated_cost double not null,
      evidence_bundle_json json not null,
      lineage_refs_json json not null,
      source_span_ids_json json not null,
      compression_ratio double not null,
      labels_json json not null,
      facets_json json not null
    )
    """,
    """
    create table if not exists classification_traces (
      classification_id varchar primary key,
      work_unit_id varchar not null,
      policy_basis varchar not null,
      work_category varchar not null,
      policy_outcome varchar not null,
      cost_category varchar not null,
      direct_cost double not null,
      indirect_cost double not null,
      blended_cost double not null,
      confidence_score double not null,
      evidence_score double not null,
      evidence_strength varchar not null,
      explanation varchar not null,
      features_used_json json not null,
      reviewer_required boolean not null,
      reviewer_status varchar not null,
      override_status varchar not null,
      policy_hint varchar not null,
      created_at timestamp not null,
      decisions_json json not null
    )
    """,
    """
    create table if not exists policy_decisions (
      decision_id varchar primary key,
      trace_id varchar not null,
      rule_id varchar not null,
      model_id varchar,
      decision_type varchar not null,
      value varchar not null,
      confidence double not null,
      explanation varchar not null,
      evidence_refs_json json not null,
      competing_candidates_json json not null,
      requires_review boolean not null,
      features_used_json json not null
    )
    """,
    """
    create table if not exists policy_runs (
      policy_run_id varchar primary key,
      policy_basis varchar not null,
      started_at timestamp not null,
      trace_count bigint not null,
      review_required_count bigint not null,
      notes varchar
    )
    """,
    """
    create table if not exists report_artifacts (
      report_id varchar primary key,
      report_kind varchar not null,
      uri varchar not null,
      content_type varchar not null,
      created_at timestamp not null,
      metadata_json json not null
    )
    """,
    """
    create table if not exists overrides (
      override_id varchar primary key,
      classification_id varchar not null,
      reviewer varchar not null,
      note varchar not null,
      work_category varchar,
      policy_outcome varchar,
      created_at timestamp not null
    )
    """,
]
