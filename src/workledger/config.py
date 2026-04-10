from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

try:
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover - fallback for lean environments
    BaseSettings = BaseModel  # type: ignore[misc,assignment]


def _settings_config_dict(**kwargs: object) -> Any:
    return dict(kwargs)


def _dotenv_values(path: Path = Path(".env")) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _env_value(name: str) -> str | None:
    return os.getenv(name) or _dotenv_values().get(name)


def _env_flag(name: str) -> bool | None:
    value = _env_value(name)
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value for {name}: {value}")


class WorkledgerConfig(BaseSettings):
    """Local project configuration for workledger."""

    model_config = _settings_config_dict(
        env_prefix="WORKLEDGER_",
        env_file=".env",
        extra="ignore",
    )

    project_dir: Path = Field(default=Path(".workledger"))
    database_path: Path | None = Field(default=None)
    raw_events_dir: Path | None = Field(default=None)
    exports_dir: Path | None = Field(default=None)
    reports_dir: Path | None = Field(default=None)
    policies_dir: Path | None = Field(default=None)
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    api_key: str | None = Field(default=None)
    allow_unauthenticated_api: bool = Field(default=False)
    max_batch_size: int = Field(default=10_000, ge=1)
    max_payload_bytes: int = Field(default=2_000_000, ge=1)
    schema_version: str = Field(default="1.0.0")

    @model_validator(mode="after")
    def _derive_paths(self) -> WorkledgerConfig:
        if self.project_dir == Path(".workledger") and (project_dir := _env_value("WORKLEDGER_PROJECT_DIR")):
            self.project_dir = Path(project_dir)
        if self.database_path is None and (database_path := _env_value("WORKLEDGER_DATABASE_PATH")):
            self.database_path = Path(database_path)
        if self.host == "127.0.0.1" and (host := _env_value("WORKLEDGER_HOST")):
            self.host = host
        if self.port == 8000 and (port := _env_value("WORKLEDGER_PORT")):
            self.port = int(port)
        if self.api_key is None and (api_key := _env_value("WORKLEDGER_API_KEY")):
            self.api_key = api_key
        if self.allow_unauthenticated_api is False and (
            allow_unauthenticated_api := _env_flag("WORKLEDGER_ALLOW_UNAUTHENTICATED_API")
        ) is not None:
            self.allow_unauthenticated_api = allow_unauthenticated_api
        if self.max_batch_size == 10_000 and (max_batch_size := _env_value("WORKLEDGER_MAX_BATCH_SIZE")):
            self.max_batch_size = int(max_batch_size)
        if self.max_payload_bytes == 2_000_000 and (max_payload_bytes := _env_value("WORKLEDGER_MAX_PAYLOAD_BYTES")):
            self.max_payload_bytes = int(max_payload_bytes)
        self.database_path = self.database_path or (self.project_dir / "workledger.duckdb")
        self.raw_events_dir = self.raw_events_dir or (self.project_dir / "raw")
        self.exports_dir = self.exports_dir or (self.project_dir / "exports")
        self.reports_dir = self.reports_dir or (self.project_dir / "reports")
        self.policies_dir = self.policies_dir or (self.project_dir / "policies")
        return self

    @classmethod
    def from_project_dir(cls, project_dir: Path) -> WorkledgerConfig:
        return cls(
            project_dir=project_dir,
            database_path=project_dir / "workledger.duckdb",
            raw_events_dir=project_dir / "raw",
            exports_dir=project_dir / "exports",
            reports_dir=project_dir / "reports",
            policies_dir=project_dir / "policies",
        )

    def ensure_dirs(self) -> None:
        for path in (
            self.project_dir,
            self.raw_events_dir,
            self.exports_dir,
            self.reports_dir,
            self.policies_dir,
        ):
            assert path is not None
            path.mkdir(parents=True, exist_ok=True)
