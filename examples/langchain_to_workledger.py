"""Minimal LangChain-style export to WorkLedger JSONL."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


def main() -> None:
    output = Path("langchain_export.jsonl")
    start = datetime.now(UTC)
    event = {
        "event_type": "observation_span",
        "source_kind": "sdk",
        "trace_id": "trace_langchain_example",
        "span_id": "span_langchain_root",
        "span_kind": "agent",
        "name": "Summarize support thread",
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(seconds=3)).isoformat(),
        "token_input": 1200,
        "token_output": 450,
        "direct_cost": 0.012,
        "attributes": {"task_title": "Summarize support thread", "framework": "langchain"},
        "facets": {"langchain": {"chain": "support-summary"}},
    }
    output.write_text(json.dumps(event) + "\n", encoding="utf-8")
    print(f"Wrote {output}. Run: wl ingest {output}")


if __name__ == "__main__":
    main()
