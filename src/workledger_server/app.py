"""FastAPI server exposing workledger as a REST API."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from workledger import WorkledgerConfig, WorkledgerPipeline
from workledger.ingest.normalize import normalize_event
from workledger.policy import list_policy_packs, resolve_policy_pack_path

logger = logging.getLogger(__name__)


def create_app(config: WorkledgerConfig | None = None) -> FastAPI:
    resolved_config = config or WorkledgerConfig()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> Any:
        app.state.pipeline = WorkledgerPipeline(resolved_config)
        try:
            yield
        finally:
            app.state.pipeline.close()

    app = FastAPI(
        title="workledger",
        summary="REST API for workledger — turn AI agent traces into units of work.",
        lifespan=lifespan,
    )
    protected = APIRouter()

    def pipeline(request: Request) -> WorkledgerPipeline:
        return cast(WorkledgerPipeline, request.app.state.pipeline)

    async def verify_api_key(authorization: str | None = Header(default=None)) -> None:
        if not resolved_config.api_key:
            if resolved_config.allow_unauthenticated_api:
                return
            raise HTTPException(
                status_code=503,
                detail=(
                    "API access is disabled until WORKLEDGER_API_KEY is set "
                    "or WORKLEDGER_ALLOW_UNAUTHENTICATED_API=true."
                ),
            )
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
    def schema_versions(request: Request) -> dict[str, str]:
        return {"schema_version": pipeline(request).config.schema_version}

    @protected.get("/policies", dependencies=[Depends(verify_api_key)])
    def policies(request: Request) -> list[dict[str, Any]]:
        policies_dir = pipeline(request).config.policies_dir
        assert policies_dir is not None
        return [
            pack.model_dump(mode="json") for pack in list_policy_packs(policies_dir)
        ]

    @protected.post("/ingest/events", dependencies=[Depends(verify_api_key)])
    def ingest_events(request: Request, payloads: list[dict[str, Any]]) -> dict[str, Any]:
        if len(payloads) > resolved_config.max_batch_size:
            raise HTTPException(status_code=400, detail="batch size exceeds configured limit")
        spans = []
        errors = []
        for index, payload in enumerate(payloads, start=1):
            try:
                spans.append(normalize_event(payload))
            except (TypeError, ValueError, KeyError):
                logger.warning(
                    "Failed to normalize event at line %d",
                    index,
                    exc_info=True,
                )
                errors.append({"line": index, "error": "invalid event payload"})
        if spans:
            pipeline(request).store.save_observation_spans(spans)
        logger.info("Ingested %d events via API (skipped %d)", len(spans), len(errors))
        return {"ingested": len(spans), "skipped": len(errors), "errors": errors}

    @protected.post("/ingest/spans", dependencies=[Depends(verify_api_key)])
    def ingest_spans(request: Request, spans: list[dict[str, Any]]) -> dict[str, Any]:
        if len(spans) > resolved_config.max_batch_size:
            raise HTTPException(status_code=400, detail="batch size exceeds configured limit")
        result = pipeline(request).ingest_payloads(
            [
                {key: value for key, value in span.items() if key != "duration_ms"}
                for span in spans
            ]
        )
        return result.model_dump(mode="json", exclude={"spans"})

    @protected.post("/rollup", dependencies=[Depends(verify_api_key)])
    def run_rollup(request: Request) -> list[dict[str, Any]]:
        return [work_unit.model_dump(mode="json") for work_unit in pipeline(request).rollup()]

    @protected.post("/classify", dependencies=[Depends(verify_api_key)])
    def run_classify(request: Request, policy: str | None = None) -> list[dict[str, Any]]:
        policies_dir = pipeline(request).config.policies_dir
        assert policies_dir is not None
        try:
            policy_path = (
                resolve_policy_pack_path(policies_dir, policy).relative_to(policies_dir.resolve())
                if policy
                else None
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return [
            trace.model_dump(mode="json")
            for trace in pipeline(request).classify(policy_path)
        ]

    @protected.get("/work-units", dependencies=[Depends(verify_api_key)])
    def list_work_units(request: Request) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json")
            for item in pipeline(request).store.list_work_units()
        ]

    @protected.get("/work-units/{work_unit_id}", dependencies=[Depends(verify_api_key)])
    def get_work_unit(request: Request, work_unit_id: str) -> dict[str, Any]:
        work_unit = pipeline(request).store.get_work_unit(work_unit_id)
        if work_unit is None:
            raise HTTPException(status_code=404, detail="work unit not found")
        return work_unit.model_dump(mode="json")

    @protected.get("/classifications", dependencies=[Depends(verify_api_key)])
    def list_classifications(request: Request) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json")
            for item in pipeline(request).store.list_classifications()
        ]

    @protected.get(
        "/classifications/{classification_id}",
        dependencies=[Depends(verify_api_key)],
    )
    def get_classification(request: Request, classification_id: str) -> dict[str, Any]:
        trace = pipeline(request).store.get_classification(classification_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="classification not found")
        return trace.model_dump(mode="json")

    @protected.get("/explain/{identifier}", dependencies=[Depends(verify_api_key)])
    def explain(request: Request, identifier: str) -> dict[str, Any]:
        try:
            return pipeline(request).explain(identifier)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @protected.get("/decisions", dependencies=[Depends(verify_api_key)])
    def list_decisions(request: Request) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json") for item in pipeline(request).store.list_decisions()
        ]

    @protected.get("/reports", dependencies=[Depends(verify_api_key)])
    def list_reports(request: Request) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json") for item in pipeline(request).store.list_reports()
        ]

    @protected.get("/review-queue", dependencies=[Depends(verify_api_key)])
    def review_queue(request: Request) -> list[dict[str, Any]]:
        return pipeline(request).review_queue()

    app.include_router(protected)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    config = WorkledgerConfig()
    uvicorn.run("workledger_server.app:app", host=config.host, port=config.port, reload=False)
