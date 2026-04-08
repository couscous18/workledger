"""Minimal CrewAI-style export to WorkLedger JSONL."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


def main() -> None:
    output = Path("crewai_export.jsonl")
    start = datetime.now(UTC)
    event = {
        "event_type": "observation_span",
        "source_kind": "sdk",
        "trace_id": "trace_crewai_example",
        "span_id": "span_crewai_task",
        "span_kind": "agent",
        "name": "Draft launch brief",
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(seconds=4)).isoformat(),
        "token_input": 900,
        "token_output": 600,
        "direct_cost": 0.01,
        "attributes": {"task_title": "Draft launch brief", "framework": "crewai"},
        "facets": {"crewai": {"crew": "launch-ops"}},
    }
    output.write_text(json.dumps(event) + "\n", encoding="utf-8")
    print(f"Wrote {output}. Run: wl ingest {output}")


if __name__ == "__main__":
    main()
