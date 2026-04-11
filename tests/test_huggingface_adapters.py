from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from workledger import WorkledgerConfig, WorkledgerPipeline
from workledger.adapters.huggingface import adapt_huggingface_dataset
from workledger.cli import app
from workledger.demo import run_demo

runner = CliRunner()


class FakeDataset:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def shuffle(self, seed: int) -> FakeDataset:
        if not self.rows:
            return self
        shift = seed % len(self.rows)
        return FakeDataset(self.rows[shift:] + self.rows[:shift])

    def select(self, indexes: range) -> FakeDataset:
        return FakeDataset([self.rows[index] for index in indexes])

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, Any]:
        return self.rows[index]


def _fixture_rows(name: str) -> list[dict[str, Any]]:
    path = Path("tests/fixtures") / name
    return json.loads(path.read_text(encoding="utf-8"))


def _install_fake_load_dataset(monkeypatch: Any) -> None:
    def fake_load_dataset(dataset_id: str, split: str) -> FakeDataset:
        del split
        if dataset_id == "smolagents/gaia-traces":
            return FakeDataset(_fixture_rows("hf_gaia_sample.json"))
        if dataset_id == "kshitijthakkar/smoltrace-traces-20260130_053009":
            return FakeDataset(_fixture_rows("hf_smoltrace_sample.json"))
        raise AssertionError(f"unexpected dataset id: {dataset_id}")

    monkeypatch.setattr("workledger.adapters.huggingface.load_dataset", fake_load_dataset)


def test_gaia_adapter_maps_messages_to_huggingface_spans(monkeypatch: Any) -> None:
    _install_fake_load_dataset(monkeypatch)
    bundle = adapt_huggingface_dataset(
        dataset_id="smolagents/gaia-traces",
        split="train",
        adapter_name="gaia",
        limit=2,
        seed=7,
    )

    assert bundle.adapter_name == "gaia"
    assert len(bundle.rows) == 2
    assert any(span.source_kind == "huggingface" for span in bundle.spans)
    assert any(span.raw_payload_ref.startswith("hf://smolagents/gaia-traces/train/") for span in bundle.spans)
    assert any(span.attributes.get("review_required") for span in bundle.spans)


def test_smoltrace_adapter_preserves_trace_lineage_and_cost(monkeypatch: Any) -> None:
    _install_fake_load_dataset(monkeypatch)
    bundle = adapt_huggingface_dataset(
        dataset_id="kshitijthakkar/smoltrace-traces-20260130_053009",
        split="train",
        adapter_name="smoltrace",
        limit=2,
        seed=7,
    )

    assert bundle.adapter_name == "smoltrace"
    assert any(span.trace_id == "trace-smol-1" for span in bundle.spans)
    assert any(span.direct_cost > 0 for span in bundle.spans)
    assert any(span.facets.get("smoltrace") for span in bundle.spans)


def test_pipeline_ingest_huggingface_round_trips_into_work_units(monkeypatch: Any, tmp_path: Path) -> None:
    _install_fake_load_dataset(monkeypatch)
    config = WorkledgerConfig.from_project_dir(tmp_path / "hf-project")
    pipeline = WorkledgerPipeline(config)

    ingest = pipeline.ingest_huggingface(
        "smolagents/gaia-traces",
        adapter_name="gaia",
        split="train",
        limit=2,
        seed=7,
    )
    work_units = pipeline.rollup()
    summary = pipeline.report_engine.summary()
    pipeline.close()

    assert ingest.row_count == 2
    assert ingest.ingest.ingested >= 4
    assert work_units
    assert summary["dataset_context"][0]["dataset_id"] == "smolagents/gaia-traces"
    assert summary["review_needed_work"]
    assert any(
        ref.startswith("hf://smolagents/gaia-traces/train/")
        for work_unit in work_units
        for ref in work_unit.lineage_refs
    )


def test_cli_ingest_hf_reports_adapter_and_saved_rows(monkeypatch: Any, tmp_path: Path) -> None:
    _install_fake_load_dataset(monkeypatch)

    result = runner.invoke(
        app,
        [
            "ingest-hf",
            "smolagents/gaia-traces",
            "--adapter",
            "gaia",
            "--split",
            "train",
            "--limit",
            "2",
            "--project-dir",
            str(tmp_path / "cli-project"),
        ],
    )

    assert result.exit_code == 0
    assert "adapter gaia" in result.stdout.lower()
    assert "saved sampled rows" in result.stdout.lower()


def test_cli_hf_demos_run_without_classification_by_default(monkeypatch: Any, tmp_path: Path) -> None:
    _install_fake_load_dataset(monkeypatch)

    gaia = run_demo("hf-gaia", tmp_path / "hf-gaia")
    smoltrace = run_demo("hf-smoltrace", tmp_path / "hf-smoltrace")

    assert gaia["dataset_id"] == "smolagents/gaia-traces"
    assert gaia["classifications"] == []
    assert gaia["summary"]["review_needed_work"]
    assert "comparative_economics" not in gaia["summary"]

    assert smoltrace["dataset_id"] == "kshitijthakkar/smoltrace-traces-20260130_053009"
    assert smoltrace["classifications"] == []
    assert smoltrace["work_units"]
