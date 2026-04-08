from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from workledger import WorkledgerConfig, WorkledgerPipeline
from workledger.demo import support_demo_events


def main() -> None:
    with TemporaryDirectory(prefix="workledger-tiny-") as tmpdir:
        config = WorkledgerConfig.from_project_dir(Path(tmpdir) / "project")
        pipeline = WorkledgerPipeline(config)
        input_path = config.raw_events_dir / "support.jsonl"
        payload = "\n".join(json.dumps(event) for event in support_demo_events()) + "\n"
        input_path.write_text(payload, encoding="utf-8")

        pipeline.ingest(input_path)
        work_units = pipeline.rollup()
        traces = pipeline.classify()
        pipeline.report(include_economics=True)
        queue = pipeline.review_queue()

        for work_unit, trace in zip(work_units, traces, strict=False):
            print(
                f"- {work_unit.title} -> "
                f"{trace.work_category} / {trace.policy_outcome} "
                f"(confidence={trace.confidence_score:.2f})"
            )

        print(f"pending review items: {len(queue)}")
        pipeline.close()


if __name__ == "__main__":
    main()
