"""Shared JSON Schema generation for the public workledger data model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from workledger.models import (
    ClassificationTrace,
    EvidenceRef,
    ObservationSpan,
    PolicyDecision,
    PolicyPack,
    PolicyRun,
    ReportArtifact,
    ReviewOverride,
    WorkUnit,
)


def core_schema_models() -> dict[str, type[BaseModel]]:
    return {
        "ObservationSpan": ObservationSpan,
        "WorkUnit": WorkUnit,
        "ClassificationTrace": ClassificationTrace,
        "PolicyDecision": PolicyDecision,
        "EvidenceRef": EvidenceRef,
        "PolicyPack": PolicyPack,
        "PolicyRun": PolicyRun,
        "ReportArtifact": ReportArtifact,
        "ReviewOverride": ReviewOverride,
    }


def generate_schema_bundle(
    models: dict[str, type[BaseModel]] | None = None,
) -> dict[str, Any]:
    selected_models = models or core_schema_models()
    definitions = {
        name: model.model_json_schema(ref_template="#/definitions/{model}")
        for name, model in selected_models.items()
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://raw.githubusercontent.com/couscous18/workledger/main/schemas/workledger.schema.json",
        "title": "workledger core schema",
        "type": "object",
        "description": "Combined schema definitions for core V1 workledger objects.",
        "definitions": definitions,
    }


def write_schema_bundle(
    destination: Path,
    models: dict[str, type[BaseModel]] | None = None,
) -> Path:
    destination.write_text(
        json.dumps(generate_schema_bundle(models), indent=2) + "\n",
        encoding="utf-8",
    )
    return destination
