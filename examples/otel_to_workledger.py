"""Minimal OpenTelemetry-like payload for WorkLedger ingest."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


def main() -> None:
    output = Path("otel_export.json")
    start = datetime.now(UTC)
    payload = [
        {
            "traceId": "trace_otel_example",
            "spanId": "span_otel_root",
            "name": "Generate release notes",
            "kind": "server",
            "startTime": start.isoformat(),
            "endTime": (start + timedelta(seconds=2)).isoformat(),
            "attributes": [
                {"key": "openinference.span.kind", "value": {"stringValue": "agent"}},
                {"key": "llm.model_name", "value": {"stringValue": "gpt-4.1-mini"}},
                {"key": "llm.token_count.prompt", "value": {"intValue": 500}},
                {"key": "llm.token_count.completion", "value": {"intValue": 300}},
                {"key": "llm.cost.usd", "value": {"doubleValue": 0.006}},
            ],
        }
    ]
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {output}. Run: wl ingest {output}")


if __name__ == "__main__":
    main()
