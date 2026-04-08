from pathlib import Path

from workledger.benchmark import (
    _safe_divide,
    load_benchmark_suite,
    render_benchmark_markdown,
    run_benchmark,
    run_benchmark_suite,
    write_benchmark_report,
)


def test_capex_benchmark_metrics(tmp_path: Path) -> None:
    suite = load_benchmark_suite(Path("benchmark-data/software_capex_review_v1"))
    result = run_benchmark_suite(suite)

    assert result.total_cases == 4
    assert result.class_accuracy == 1.0
    assert result.treatment_accuracy == 1.0
    assert result.reviewer_precision == 1.0
    assert result.reviewer_recall == 1.0
    assert result.average_compression_ratio > 1.0
    assert result.mismatches == []

    markdown = render_benchmark_markdown(result)
    assert "software_capex_review_v1" in markdown
    assert "average compression ratio" in markdown
    assert "none" in markdown

    json_path = write_benchmark_report(result, tmp_path / "benchmark.json", "json")
    md_path = write_benchmark_report(result, tmp_path / "benchmark.md", "markdown")
    assert json_path.exists()
    assert md_path.exists()


def test_capex_benchmark_confusion_tables_are_stable() -> None:
    result = run_benchmark_suite(Path("benchmark-data/software_capex_review_v1"))
    assert len(result.work_category_confusion) >= 4
    assert len(result.treatment_confusion) >= 3
    assert any(row["actual"] == "unknown" for row in result.work_category_confusion)


def test_run_benchmark_accepts_manifest_file_path() -> None:
    manifest_path = Path("benchmark-data/software_capex_review_v1/manifest.json")
    result = run_benchmark(manifest_path)

    assert result.benchmark_id == "software_capex_review_v1"
    assert result.total_cases == 4
    assert result.class_accuracy == 1.0


def test_safe_divide_does_not_report_perfection_when_denominator_is_zero() -> None:
    assert _safe_divide(0, 0) == 0.0
    assert _safe_divide(3, 0) == 0.0
