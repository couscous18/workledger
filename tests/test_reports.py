from pathlib import Path

import pytest

from workledger.demo import run_demo


def test_report_bundle_writes_expected_files(tmp_path: Path) -> None:
    result = run_demo("all", tmp_path / "demo")
    report_uris = {Path(item["uri"]).name for item in result["reports"]}
    assert "summary.json" in report_uris
    assert "summary.md" in report_uris
    assert "summary.html" in report_uris
    assert "classification_traces.parquet" in report_uris


def test_capex_report_includes_queue_and_compression_story(tmp_path: Path) -> None:
    result = run_demo("capex", tmp_path / "capex-demo")
    summary = result["summary"]

    assert any(
        item["policy_outcome"] == "maintenance_non_capitalizable"
        for item in result["classifications"]
    )
    assert any(
        item["policy_outcome"] == "capitalize_candidate"
        for item in result["classifications"]
    )
    assert any(item["reviewer_required"] for item in result["classifications"])
    assert summary["pending_review_queue"]
    assert summary["top_ambiguous_items"]
    assert summary["compression_story"]["max_compression_ratio"] > 1.0

    markdown_path = next(
        Path(item["uri"])
        for item in result["reports"]
        if item["report_kind"] == "markdown_summary"
    )
    html_path = next(
        Path(item["uri"])
        for item in result["reports"]
        if item["report_kind"] == "html_summary"
    )
    markdown = markdown_path.read_text(encoding="utf-8")
    html = html_path.read_text(encoding="utf-8")

    assert "Cost by Policy Outcome" in markdown
    assert "Pending Review Queue" in markdown
    assert "Compression Proof Point" in markdown
    assert "Pending Review Queue" in html
    assert "Compression Proof Point" in html


@pytest.mark.parametrize("demo_name", ["coding", "marketing", "support"])
def test_named_demo_variants_smoke(tmp_path: Path, demo_name: str) -> None:
    result = run_demo(demo_name, tmp_path / f"{demo_name}-demo")

    assert result["classifications"]
    assert result["work_units"]
    assert result["reports"]
    assert result["summary"]["totals"]["work_unit_count"] >= 1
