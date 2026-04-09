"""Load public Hugging Face traces and roll them into work units."""

from __future__ import annotations

from pathlib import Path

from workledger import WorkledgerConfig, WorkledgerPipeline


def main() -> None:
    project_dir = Path(".workledger/examples/hf-gaia")
    pipeline = WorkledgerPipeline(WorkledgerConfig.from_project_dir(project_dir))
    try:
        pipeline.ingest_huggingface(
            "smolagents/gaia-traces",
            adapter_name="gaia",
            split="train",
            limit=3,
            seed=7,
        )
        work_units = pipeline.rollup()
        pipeline.report()
        for work_unit in work_units:
            print(
                f"{work_unit.title} | {work_unit.kind} | "
                f"review={work_unit.review_state} | evidence={len(work_unit.evidence_bundle)}"
            )
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
