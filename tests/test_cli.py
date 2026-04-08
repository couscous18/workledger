from pathlib import Path

from typer.testing import CliRunner

from workledger import WorkledgerConfig, WorkledgerPipeline
from workledger.cli import app
from workledger.demo import run_demo
from workledger.review import apply_override

runner = CliRunner()


def test_review_queue_cli_shows_pending_items_and_hides_overridden(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo"
    run_demo("capex", project_dir)

    pipeline = WorkledgerPipeline(WorkledgerConfig.from_project_dir(project_dir))
    queue = pipeline.review_queue()
    assert len(queue) == 1
    assert queue[0]["title"] == "Automate release checklist workflow"
    pipeline.close()

    result = runner.invoke(app, ["review-queue", "--project-dir", str(project_dir)])
    assert result.exit_code == 0
    assert "pending review queue" in result.stdout.lower()

    pipeline = WorkledgerPipeline(WorkledgerConfig.from_project_dir(project_dir))
    queue = pipeline.review_queue()
    apply_override(
        pipeline.store,
        classification_id=queue[0]["classification_id"],
        reviewer="controller",
        note="Reviewed and accepted as capex candidate.",
    )
    pipeline.close()

    post_override = runner.invoke(app, ["review-queue", "--project-dir", str(project_dir)])
    assert post_override.exit_code == 0
    assert "No pending review items." in post_override.stdout


def test_benchmark_cli_renders_markdown(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark.md"
    result = runner.invoke(
        app,
        [
            "benchmark",
            "benchmark-data/software_capex_review_v1",
            "--format",
            "markdown",
            "--output",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    assert "Benchmark: software_capex_review_v1" in result.stdout
    assert output_path.exists()


def test_compare_costs_cli_renders_summary(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo"
    run_demo("all", project_dir)

    result = runner.invoke(app, ["compare-costs", "--from-project", str(project_dir)])
    assert result.exit_code == 0
    assert "comparative economics" in result.stdout.lower()
    assert "open hosted" in result.stdout.lower()
