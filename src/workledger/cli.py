"""Command-line interface for the wl tool."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from workledger import WorkledgerConfig, WorkledgerPipeline
from workledger.benchmark import render_benchmark_markdown, run_benchmark, write_benchmark_report
from workledger.demo import run_demo
from workledger.economics import CostScenario, build_comparative_economics, scenario_presets
from workledger.policy import list_policy_packs, validate_policy_pack
from workledger.review import apply_override
from workledger.schema import write_schema_bundle

app = typer.Typer(help="Open trace-to-work CLI for AI systems.")
policies_app = typer.Typer(help="Inspect and validate installed policy packs.")
app.add_typer(policies_app, name="policies")
console = Console()
ProjectDirOption = Annotated[Path, typer.Option(help="Project directory")]
DemoProjectDirOption = Annotated[Path, typer.Option(help="Output project directory")]
InputPathArgument = Annotated[
    Path, typer.Argument(exists=True, readable=True, help="JSON or JSONL input")
]
PolicyPathArgument = Annotated[Path, typer.Argument(exists=True, readable=True)]
IdentifierArgument = Annotated[str, typer.Argument(help="Work unit ID or classification ID")]
TraceIdArgument = Annotated[str, typer.Argument(help="Classification ID")]
TableArgument = Annotated[str, typer.Argument(help="Table to export")]
FormatArgument = Annotated[str, typer.Argument(help="csv, parquet, or json")]
DestinationArgument = Annotated[Path, typer.Argument(help="Output path")]
DemoNameArgument = Annotated[
    str,
    typer.Argument(
        help=(
            "hf-gaia, hf-smoltrace, open-traces, agent-cost, capex, coding, "
            "marketing, support, or all"
        )
    ),
]
DatasetIdArgument = Annotated[str, typer.Argument(help="Public Hugging Face dataset ID")]
BenchmarkPathArgument = Annotated[
    Path, typer.Argument(exists=True, readable=True, help="Benchmark manifest or directory")
]
PolicyPathOption = Annotated[Path | None, typer.Option(help="Path to policy pack")]
OpenReportOption = Annotated[bool, typer.Option(help="Print the HTML report path after generation")]
ReviewerOption = Annotated[str, typer.Option(help="Reviewer name")]
NoteOption = Annotated[str, typer.Option(help="Override note")]
WorkCategoryOption = Annotated[str | None, typer.Option(help="Override work category")]
PolicyOutcomeOption = Annotated[
    str | None,
    typer.Option(help="Override policy outcome"),
]
BenchmarkFormatOption = Annotated[
    str,
    typer.Option("--format", help="json or markdown"),
]
OutputPathOption = Annotated[Path | None, typer.Option(help="Optional output path")]
LimitOption = Annotated[int, typer.Option(help="Maximum items to display")]
ScenarioOption = Annotated[
    list[str],
    typer.Option("--scenario", help="Comparison preset to use. Repeatable."),
]
FormatOption = Annotated[str, typer.Option("--format", help="table or json")]
AdapterOption = Annotated[
    str,
    typer.Option("--adapter", help="auto, gaia, or smoltrace"),
]
SplitOption = Annotated[str, typer.Option(help="Dataset split to load")]
SampleLimitOption = Annotated[int | None, typer.Option(help="Maximum rows to sample")]
SeedOption = Annotated[int, typer.Option(help="Random seed for deterministic sampling")]
IncludeEconomicsOption = Annotated[
    bool,
    typer.Option(help="Include comparative economics in generated report artifacts"),
]


def _pipeline(project_dir: Path) -> WorkledgerPipeline:
    return WorkledgerPipeline(WorkledgerConfig.from_project_dir(project_dir))


def _build_scenarios(
    names: list[str],
    input_rate_per_1m: float | None,
    output_rate_per_1m: float | None,
    fixed_overhead: float | None,
) -> list[CostScenario]:
    presets = scenario_presets()
    selected_names = names or ["open_hosted", "self_hosted_gpu"]
    scenarios: list[CostScenario] = []
    for index, name in enumerate(selected_names):
        if name not in presets:
            raise typer.BadParameter(f"unknown scenario preset: {name}")
        scenario = presets[name]
        if index == 0 and (
            input_rate_per_1m is not None
            or output_rate_per_1m is not None
            or fixed_overhead is not None
        ):
            scenario = CostScenario(
                name=scenario.name,
                label=scenario.label,
                input_cost_per_1m=input_rate_per_1m
                if input_rate_per_1m is not None
                else scenario.input_cost_per_1m,
                output_cost_per_1m=output_rate_per_1m
                if output_rate_per_1m is not None
                else scenario.output_cost_per_1m,
                fixed_overhead=fixed_overhead
                if fixed_overhead is not None
                else scenario.fixed_overhead,
                description=scenario.description,
            )
        scenarios.append(scenario)
    return scenarios


@app.command()
def init(project_dir: ProjectDirOption = Path(".workledger")) -> None:
    """Initialize a local workledger project."""
    pipeline = _pipeline(project_dir)
    pipeline.init_project()
    schema_path = project_dir / "schemas.json"
    write_schema_bundle(schema_path)
    console.print(f"Initialized workledger project at [bold]{project_dir}[/bold]")
    console.print(f"Exported schemas to [bold]{schema_path}[/bold]")
    pipeline.close()


@app.command()
def ingest(
    path: InputPathArgument,
    project_dir: ProjectDirOption = Path(".workledger"),
) -> None:
    """Ingest spans from JSON, JSONL, OpenInference, OTEL, or CloudEvents payloads."""
    pipeline = _pipeline(project_dir)
    result = pipeline.ingest(path)
    console.print(
        f"Ingested [bold]{result.ingested}[/bold] spans from [bold]{path}[/bold]"
        f" and skipped [bold]{result.skipped}[/bold]."
    )
    if result.errors:
        console.print("Errors:")
        for error in result.errors[:10]:
            location = f"line {error.line}" if error.line is not None else "input"
            console.print(f"- {location}: {error.error}")
    pipeline.close()


@app.command("ingest-hf")
def ingest_hf(
    dataset_id: DatasetIdArgument,
    project_dir: ProjectDirOption = Path(".workledger"),
    adapter: AdapterOption = "auto",
    split: SplitOption = "train",
    limit: SampleLimitOption = None,
    seed: SeedOption = 7,
) -> None:
    """Ingest public Hugging Face trace datasets into normalized observations."""
    pipeline = _pipeline(project_dir)
    result = pipeline.ingest_huggingface(
        dataset_id,
        adapter_name=adapter,
        split=split,
        limit=limit,
        seed=seed,
    )
    console.print(
        f"Ingested [bold]{result.ingest.ingested}[/bold] spans from "
        f"[bold]{result.dataset_id}[/bold] ([bold]{result.row_count}[/bold] rows, "
        f"adapter [bold]{result.adapter_name}[/bold])."
    )
    console.print(f"Saved sampled rows to [bold]{result.raw_path}[/bold]")
    pipeline.close()


@app.command()
def rollup(project_dir: ProjectDirOption = Path(".workledger")) -> None:
    """Roll up noisy spans into work units."""
    pipeline = _pipeline(project_dir)
    work_units = pipeline.rollup()
    table = Table(title="work units")
    table.add_column("work unit")
    table.add_column("kind")
    table.add_column("cost", justify="right")
    table.add_column("compression", justify="right")
    for work_unit in work_units:
        table.add_row(
            work_unit.title,
            work_unit.kind,
            f"${work_unit.total_cost:.4f}",
            f"{work_unit.compression_ratio:.2f}x",
        )
    console.print(table)
    pipeline.close()


@app.command()
def classify(
    project_dir: ProjectDirOption = Path(".workledger"),
    policy_path: PolicyPathOption = None,
) -> None:
    """Run policy-backed classification on work units."""
    pipeline = _pipeline(project_dir)
    traces = pipeline.classify(policy_path)
    table = Table(title="classifications")
    table.add_column("work unit id")
    table.add_column("work category")
    table.add_column("policy outcome")
    table.add_column("blended cost", justify="right")
    table.add_column("confidence", justify="right")
    table.add_column("review", justify="right")
    for trace in traces:
        table.add_row(
            trace.work_unit_id,
            trace.work_category,
            trace.policy_outcome,
            f"${trace.blended_cost:.4f}",
            f"{trace.confidence_score:.2f}",
            "yes" if trace.reviewer_required else "no",
        )
    console.print(table)
    pipeline.close()


@app.command()
def report(
    project_dir: ProjectDirOption = Path(".workledger"),
    include_economics: IncludeEconomicsOption = False,
) -> None:
    """Generate report artifacts and render a terminal summary."""
    pipeline = _pipeline(project_dir)
    artifacts = pipeline.report(include_economics=include_economics)
    pipeline.report_engine.render_terminal(console)
    console.print("\nGenerated report artifacts:")
    for artifact in artifacts:
        console.print(f"- {artifact.report_kind}: {artifact.uri}")
    pipeline.close()


@policies_app.command("list")
def policies_list(project_dir: ProjectDirOption = Path(".workledger")) -> None:
    """List installed policy packs."""
    config = WorkledgerConfig.from_project_dir(project_dir)
    policies_dir = config.policies_dir
    assert policies_dir is not None
    table = Table(title="policy packs")
    table.add_column("basis")
    table.add_column("version")
    table.add_column("title")
    for pack in list_policy_packs(policies_dir):
        table.add_row(pack.basis, pack.version, pack.title)
    console.print(table)


@policies_app.command("validate")
def policies_validate(path: PolicyPathArgument) -> None:
    """Validate a policy pack."""
    ok, errors = validate_policy_pack(path)
    if ok:
        console.print(f"[green]valid[/green] {path}")
        raise typer.Exit(0)
    console.print(f"[red]invalid[/red] {path}")
    for error in errors:
        console.print(f"- {error}")
    raise typer.Exit(1)


@app.command()
def explain(
    identifier: IdentifierArgument,
    project_dir: ProjectDirOption = Path(".workledger"),
) -> None:
    """Explain a work unit or classification."""
    pipeline = _pipeline(project_dir)
    payload = pipeline.explain(identifier)
    console.print_json(json.dumps(payload))
    pipeline.close()


@app.command()
def export(
    table: TableArgument,
    fmt: FormatArgument,
    destination: DestinationArgument,
    project_dir: ProjectDirOption = Path(".workledger"),
) -> None:
    """Export a table from the local analytical store."""
    pipeline = _pipeline(project_dir)
    path = pipeline.export(table, fmt, destination)
    console.print(f"Exported [bold]{table}[/bold] to [bold]{path}[/bold]")
    pipeline.close()


@app.command()
def demo(
    name: DemoNameArgument = "all",
    project_dir: DemoProjectDirOption = Path(".workledger/demo"),
    policy_path: PolicyPathOption = None,
    open_report: OpenReportOption = False,
) -> None:
    """Run a local end-to-end demo with realistic fixture traces."""
    result = run_demo(name, project_dir, policy_path=policy_path)
    console.print(f"Demo [bold]{name}[/bold] complete.")
    console.print(f"Ingested data: [bold]{result['input_path']}[/bold]")
    if "dataset_id" in result:
        console.print(
            f"Dataset: [bold]{result['dataset_id']}[/bold] via adapter "
            f"[bold]{result['adapter_name']}[/bold]"
        )
    console.print(
        "Generated "
        f"{len(result['work_units'])} work units and "
        f"{len(result['classifications'])} classifications."
    )
    pipeline = _pipeline(project_dir)
    pipeline.report_engine.render_terminal(console)
    pipeline.close()
    if open_report:
        html_report = next(
            artifact["uri"]
            for artifact in result["reports"]
            if artifact["report_kind"] == "html_summary"
        )
        console.print(f"HTML report: [bold]{html_report}[/bold]")


@app.command("compare-costs")
def compare_costs(
    from_project: ProjectDirOption = Path(".workledger"),
    scenario: ScenarioOption | None = None,
    input_rate_per_1m: Annotated[
        float | None, typer.Option(help="Override input token rate for the first scenario.")
    ] = None,
    output_rate_per_1m: Annotated[
        float | None, typer.Option(help="Override output token rate for the first scenario.")
    ] = None,
    fixed_overhead: Annotated[
        float | None, typer.Option(help="Override fixed overhead for the first scenario.")
    ] = None,
    fmt: FormatOption = "table",
) -> None:
    """Compare observed AI spend with transparent open/self-hosted cost scenarios."""
    pipeline = _pipeline(from_project)
    scenarios = _build_scenarios(
        scenario or [], input_rate_per_1m, output_rate_per_1m, fixed_overhead
    )
    comparison = build_comparative_economics(
        pipeline.store.fetch_spans(),
        pipeline.store.list_work_units(),
        pipeline.store.list_classifications(),
        scenarios,
    )
    pipeline.close()
    if not comparison:
        console.print("No spans found in the selected project.")
        raise typer.Exit(1)

    if fmt == "json":
        console.print_json(json.dumps(comparison))
        return

    observed = comparison["observed"]
    totals = Table(title="observed usage")
    totals.add_column("metric")
    totals.add_column("value", justify="right")
    totals.add_row("input tokens", str(observed["input_tokens"]))
    totals.add_row("output tokens", str(observed["output_tokens"]))
    totals.add_row("observed direct cost", f"${observed['observed_direct_cost']:.4f}")
    totals.add_row("work units", str(observed["work_unit_count"]))
    console.print(totals)

    scenario_table = Table(title="comparative economics")
    scenario_table.add_column("scenario")
    scenario_table.add_column("estimated cost", justify="right")
    scenario_table.add_column("savings delta", justify="right")
    scenario_table.add_column("savings %", justify="right")
    scenario_table.add_column("cost / 1M", justify="right")
    for row in comparison["comparisons"]:
        scenario_table.add_row(
            row["label"],
            f"${row['total_cost']:.4f}",
            f"${row['savings_delta']:.4f}",
            f"{row['savings_percent']:.2f}%",
            f"${row['cost_per_1m_tokens']:.2f}",
        )
    console.print(scenario_table)

    if comparison["category_breakdown"]:
        breakdown = Table(title="category breakdown")
        breakdown.add_column("title")
        breakdown.add_column("category")
        breakdown.add_column("observed", justify="right")
        breakdown.add_column("best alternative", justify="right")
        for row in comparison["category_breakdown"][:10]:
            best = min(row["scenarios"], key=lambda item: item["estimated_cost"])
            breakdown.add_row(
                row["title"],
                row["work_category"],
                f"${row['observed_cost']:.4f}",
                f"{best['label']} ${best['estimated_cost']:.4f}",
            )
        console.print(breakdown)

    console.print("Caveats:")
    for caveat in comparison["caveats"]:
        console.print(f"- {caveat}")


@app.command("review-queue")
def review_queue(
    project_dir: ProjectDirOption = Path(".workledger"),
    limit: LimitOption = 10,
) -> None:
    """Show pending review items ranked by urgency."""
    pipeline = _pipeline(project_dir)
    items = pipeline.review_queue(limit=limit if limit > 0 else None)
    if not items:
        console.print("No pending review items.")
        pipeline.close()
        return
    table = Table(title="pending review queue")
    table.add_column("title")
    table.add_column("category")
    table.add_column("outcome")
    table.add_column("cost", justify="right")
    table.add_column("confidence", justify="right")
    table.add_column("spans", justify="right")
    table.add_column("compression", justify="right")
    table.add_column("competing")
    for item in items:
        competing = ", ".join(
            f"{candidate['value']} ({float(candidate.get('confidence', 0.0)):.2f})"
            for candidate in item["competing_candidates"][:2]
        )
        table.add_row(
            item["title"],
            item["work_category"],
            item["policy_outcome"],
            f"${item['blended_cost']:.4f}",
            f"{item['confidence_score']:.2f}",
            str(item["source_span_count"]),
            f"{item['compression_ratio']:.2f}x",
            competing or "-",
        )
    console.print(table)
    pipeline.close()


@app.command()
def benchmark(
    dataset_path: BenchmarkPathArgument,
    policy_path: PolicyPathOption = None,
    fmt: BenchmarkFormatOption = "json",
    output: OutputPathOption = None,
) -> None:
    """Evaluate a labeled benchmark dataset against a policy pack."""
    normalized_fmt = fmt.lower()
    if normalized_fmt not in {"json", "markdown"}:
        raise typer.BadParameter("format must be json or markdown")
    result = run_benchmark(dataset_path, policy_path=policy_path)
    if output is not None:
        write_benchmark_report(result, output, normalized_fmt)
        console.print(f"Wrote benchmark report to [bold]{output}[/bold]")
    if normalized_fmt == "markdown":
        console.print(render_benchmark_markdown(result))
        return
    console.print_json(json.dumps(result.to_dict()))


@app.command()
def doctor(project_dir: ProjectDirOption = Path(".workledger")) -> None:
    """Check local environment and project health."""
    required_modules = ["pydantic", "duckdb", "fastapi", "typer", "rich", "yaml"]
    table = Table(title="doctor")
    table.add_column("check")
    table.add_column("status")
    for module_name in required_modules:
        status = "ok" if importlib.util.find_spec(module_name) else "missing"
        table.add_row(f"python module: {module_name}", status)
    config = WorkledgerConfig.from_project_dir(project_dir)
    policies_dir = config.policies_dir
    assert policies_dir is not None
    table.add_row("project dir", "ok" if config.project_dir.exists() else "missing")
    table.add_row("policies", "ok" if policies_dir.exists() else "missing")
    console.print(table)


@app.command()
def override(
    trace_id: TraceIdArgument,
    reviewer: ReviewerOption,
    note: NoteOption,
    work_category: WorkCategoryOption = None,
    policy_outcome: PolicyOutcomeOption = None,
    project_dir: ProjectDirOption = Path(".workledger"),
) -> None:
    """Apply a reviewer override while preserving history."""
    pipeline = _pipeline(project_dir)
    override_record = apply_override(
        pipeline.store,
        classification_id=trace_id,
        reviewer=reviewer,
        note=note,
        work_category=work_category,
        policy_outcome=policy_outcome,
    )
    console.print_json(json.dumps(override_record.model_dump(mode="json")))
    pipeline.close()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
