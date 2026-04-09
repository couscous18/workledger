"""FastAPI server exposing workledger as a REST API."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from workledger import WorkledgerConfig, WorkledgerPipeline
from workledger.ingest.normalize import normalize_event
from workledger.policy import list_policy_packs

logger = logging.getLogger(__name__)


def create_app(config: WorkledgerConfig | None = None) -> FastAPI:
    resolved_config = config or WorkledgerConfig()
    app = FastAPI(
        title="workledger",
        summary="REST API for workledger — turn AI agent traces into units of work.",
    )
    pipeline = WorkledgerPipeline(resolved_config)
    protected = APIRouter()

    async def verify_api_key(authorization: str | None = Header(default=None)) -> None:
        if not resolved_config.api_key:
            return
        expected = f"Bearer {resolved_config.api_key}"
        if authorization != expected:
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.middleware("http")
    async def payload_limit_middleware(request: Request, call_next: Any) -> Any:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > resolved_config.max_payload_bytes:
            return JSONResponse(status_code=413, content={"detail": "payload too large"})
        return await call_next(request)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @protected.get("/schema-versions", dependencies=[Depends(verify_api_key)])
    def schema_versions() -> dict[str, str]:
        return {"schema_version": pipeline.config.schema_version}

    @protected.get("/policies", dependencies=[Depends(verify_api_key)])
    def policies() -> list[dict[str, Any]]:
        policies_dir = pipeline.config.policies_dir
        assert policies_dir is not None
        return [
            pack.model_dump(mode="json") for pack in list_policy_packs(policies_dir)
        ]

    @protected.post("/ingest/events", dependencies=[Depends(verify_api_key)])
    def ingest_events(payloads: list[dict[str, Any]]) -> dict[str, Any]:
        if len(payloads) > resolved_config.max_batch_size:
            raise HTTPException(status_code=400, detail="batch size exceeds configured limit")
        spans = []
        errors = []
        for index, payload in enumerate(payloads, start=1):
            try:
                spans.append(normalize_event(payload))
            except (TypeError, ValueError, KeyError) as exc:
                logger.warning(
                    "Failed to normalize event at line %d",
                    index,
                    exc_info=True,
                )
                errors.append({"line": index, "error": "invalid event payload"})
        if spans:
            pipeline.store.save_observation_spans(spans)
        logger.info("Ingested %d events via API (skipped %d)", len(spans), len(errors))
        return {"ingested": len(spans), "skipped": len(errors), "errors": errors}

    @protected.post("/ingest/spans", dependencies=[Depends(verify_api_key)])
    def ingest_spans(spans: list[dict[str, Any]]) -> dict[str, Any]:
        if len(spans) > resolved_config.max_batch_size:
            raise HTTPException(status_code=400, detail="batch size exceeds configured limit")
        result = pipeline.ingest_payloads(
            [
                {key: value for key, value in span.items() if key != "duration_ms"}
                for span in spans
            ]
        )
        return result.model_dump(mode="json", exclude={"spans"})

    @protected.post("/rollup", dependencies=[Depends(verify_api_key)])
    def run_rollup() -> list[dict[str, Any]]:
        return [work_unit.model_dump(mode="json") for work_unit in pipeline.rollup()]

    @protected.post("/classify", dependencies=[Depends(verify_api_key)])
    def run_classify(policy_path: str | None = None) -> list[dict[str, Any]]:
        policy: Path | None = None
        if policy_path:
            candidate = Path(policy_path)
            if candidate.is_absolute() or ".." in candidate.parts:
                raise HTTPException(status_code=400, detail="invalid policy_path")
            policy = candidate
        return [trace.model_dump(mode="json") for trace in pipeline.classify(policy)]

    @protected.get("/work-units", dependencies=[Depends(verify_api_key)])
    def list_work_units() -> list[dict[str, Any]]:
        return [item.model_dump(mode="json") for item in pipeline.store.list_work_units()]

    @protected.get("/work-units/{work_unit_id}", dependencies=[Depends(verify_api_key)])
    def get_work_unit(work_unit_id: str) -> dict[str, Any]:
        work_unit = pipeline.store.get_work_unit(work_unit_id)
        if work_unit is None:
            raise HTTPException(status_code=404, detail="work unit not found")
        return work_unit.model_dump(mode="json")

    @protected.get("/classifications", dependencies=[Depends(verify_api_key)])
    def list_classifications() -> list[dict[str, Any]]:
        return [item.model_dump(mode="json") for item in pipeline.store.list_classifications()]

    @protected.get(
        "/classifications/{classification_id}",
        dependencies=[Depends(verify_api_key)],
    )
    def get_classification(classification_id: str) -> dict[str, Any]:
        trace = pipeline.store.get_classification(classification_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="classification not found")
        return trace.model_dump(mode="json")

    @protected.get("/decisions", dependencies=[Depends(verify_api_key)])
    def list_decisions() -> list[dict[str, Any]]:
        return [item.model_dump(mode="json") for item in pipeline.store.list_decisions()]

    @protected.get("/reports", dependencies=[Depends(verify_api_key)])
    def list_reports() -> list[dict[str, Any]]:
        return [item.model_dump(mode="json") for item in pipeline.store.list_reports()]

    @protected.get("/review-queue", dependencies=[Depends(verify_api_key)])
    def review_queue() -> list[dict[str, Any]]:
        return pipeline.review_queue()

    app.include_router(protected)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    config = WorkledgerConfig()
    uvicorn.run("workledger_server.app:app", host=config.host, port=config.port, reload=False)
