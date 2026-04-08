from pathlib import Path

from fastapi.testclient import TestClient

from workledger import WorkledgerConfig, WorkledgerPipeline
from workledger.demo import demo_events
from workledger.ingest.normalize import normalize_event
from workledger_server.app import create_app


def test_review_queue_endpoint_empty_and_populated(tmp_path: Path) -> None:
    config = WorkledgerConfig.from_project_dir(tmp_path / "api")
    client = TestClient(create_app(config))

    empty_response = client.get("/review-queue")
    assert empty_response.status_code == 200
    assert empty_response.json() == []

    ingest = client.post("/ingest/events", json=demo_events("capex"))
    assert ingest.status_code == 200
    assert ingest.json()["ingested"] >= 1

    rollup = client.post("/rollup")
    assert rollup.status_code == 200
    assert len(rollup.json()) == 3

    classify = client.post(
        "/classify",
        params={"policy_path": str(Path("policies/software_capex_review_v1.yaml").resolve())},
    )
    assert classify.status_code == 200

    queue_response = client.get("/review-queue")
    assert queue_response.status_code == 200
    payload = queue_response.json()
    assert len(payload) == 1
    assert payload[0]["title"] == "Automate release checklist workflow"


def test_ingest_spans_accepts_canonical_spans_without_renormalizing(tmp_path: Path) -> None:
    config = WorkledgerConfig.from_project_dir(tmp_path / "api")
    client = TestClient(create_app(config))
    canonical_span = normalize_event(demo_events("support")[0]).model_dump(mode="json")
    canonical_span["source_kind"] = "manual"

    ingest = client.post("/ingest/spans", json=[canonical_span])
    assert ingest.status_code == 200

    pipeline = WorkledgerPipeline(config)
    spans = pipeline.store.fetch_spans()
    pipeline.close()

    assert len(spans) == 1
    assert spans[0].source_kind == "manual"


def test_server_requires_api_key_when_configured(tmp_path: Path) -> None:
    config = WorkledgerConfig.from_project_dir(tmp_path / "api")
    config.api_key = "secret"
    client = TestClient(create_app(config))

    unauthorized = client.get("/work-units")
    assert unauthorized.status_code == 401

    authorized = client.get("/work-units", headers={"Authorization": "Bearer secret"})
    assert authorized.status_code == 200


def test_server_rejects_oversized_batch(tmp_path: Path) -> None:
    config = WorkledgerConfig.from_project_dir(tmp_path / "api")
    config.max_batch_size = 1
    client = TestClient(create_app(config))
    response = client.post("/ingest/events", json=demo_events("support"))
    assert response.status_code == 400
