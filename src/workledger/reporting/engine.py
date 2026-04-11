"""Generate reports in multiple formats (terminal, JSON, CSV, Parquet, Markdown, HTML)."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from html import escape
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from workledger.economics import build_comparative_economics, scenario_presets
from workledger.models import ClassificationTrace, ObservationSpan, ReportArtifact, WorkUnit
from workledger.review import review_queue_items
from workledger.storage import DuckDBStore


def _format_candidates(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "-"
    return ", ".join(
        f"{item.get('value', 'unknown')} ({float(item.get('confidence', 0.0)):.2f})"
        for item in candidates[:2]
    )


def _format_gap(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


class ReportEngine:
    def __init__(self, store: DuckDBStore) -> None:
        self.store = store

    def summary(self, *, include_economics: bool = False) -> dict[str, Any]:
        spans = self.store.fetch_spans()
        work_units = self.store.list_work_units()
        traces = self.store.list_classifications()
        review_queue = review_queue_items(self.store, limit=10)
        work_unit_by_id = {item.work_unit_id: item for item in work_units}

        category_totals: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"work_category": "", "blended_cost": 0.0, "work_units": 0}
        )
        trust_totals: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"trust_state": "", "blended_cost": 0.0, "work_units": 0}
        )
        policy_outcome_totals: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"policy_outcome": "", "blended_cost": 0.0, "work_units": 0}
        )
        low_trust_high_cost: list[dict[str, Any]] = []

        for trace in traces:
            bucket = category_totals[str(trace.work_category)]
            bucket["work_category"] = str(trace.work_category)
            bucket["blended_cost"] += trace.blended_cost
            bucket["work_units"] += 1

            outcome_bucket = policy_outcome_totals[str(trace.policy_outcome)]
            outcome_bucket["policy_outcome"] = str(trace.policy_outcome)
            outcome_bucket["blended_cost"] += trace.blended_cost
            outcome_bucket["work_units"] += 1

            work_unit = work_unit_by_id.get(trace.work_unit_id)
            if work_unit is None:
                continue

            trust_bucket = trust_totals[str(work_unit.trust_state)]
            trust_bucket["trust_state"] = str(work_unit.trust_state)
            trust_bucket["blended_cost"] += trace.blended_cost
            trust_bucket["work_units"] += 1

            if trace.blended_cost >= 0.05 and str(work_unit.trust_state) in {
                "unreviewed",
                "self_checked",
            }:
                low_trust_high_cost.append(
                    {
                        "title": work_unit.title,
                        "work_category": str(trace.work_category),
                        "blended_cost": round(trace.blended_cost, 6),
                        "trust_state": str(work_unit.trust_state),
                    }
                )

        dataset_context = self._dataset_context(spans)
        raw_trace_examples = self._raw_trace_examples(spans)
        normalized_observation_examples = self._normalized_observation_examples(spans)
        work_unit_examples = self._work_unit_examples(work_units)
        review_needed_work = self._review_needed_work(work_units, traces)

        total_direct_cost = round(
            sum(item.direct_cost for item in work_units)
            if work_units
            else sum(span.direct_cost for span in spans),
            6,
        )
        total_blended_cost = round(
            sum(trace.blended_cost for trace in traces)
            if traces
            else sum(item.total_cost for item in work_units),
            6,
        )
        avg_compression_ratio = (
            round(sum(item.compression_ratio for item in work_units) / len(work_units), 2)
            if work_units
            else 0.0
        )
        avg_confidence = (
            round(sum(item.confidence_score for item in traces) / len(traces), 3) if traces else 0.0
        )
        total_source_spans = sum(len(item.source_span_ids) for item in work_units)

        compression_proof_point = None
        if work_units:
            proof = max(
                work_units,
                key=lambda item: (item.compression_ratio, len(item.source_span_ids), item.total_cost),
            )
            compression_proof_point = {
                "work_unit_id": proof.work_unit_id,
                "title": proof.title,
                "source_span_count": len(proof.source_span_ids),
                "compression_ratio": proof.compression_ratio,
            }

        top_material_work_units = [
            {
                "work_unit_id": item.work_unit_id,
                "title": item.title,
                "importance_band": str(item.importance_band),
                "direct_cost": item.direct_cost,
                "compression_ratio": item.compression_ratio,
                "source_span_count": len(item.source_span_ids),
            }
            for item in sorted(
                work_units,
                key=lambda item: (item.direct_cost, item.importance_score, item.compression_ratio),
                reverse=True,
            )[:10]
        ]
        top_ambiguous_items = sorted(
            review_queue,
            key=lambda item: (
                item["confidence_score"],
                item["confidence_gap"] if item["confidence_gap"] is not None else 1.0,
                -item["blended_cost"],
            ),
        )[:5]

        summary = {
            "totals": {
                "work_unit_count": len(work_units),
                "total_direct_cost": total_direct_cost,
                "total_blended_cost": total_blended_cost,
                "avg_compression_ratio": avg_compression_ratio,
                "avg_confidence": avg_confidence,
                "review_burden": len(review_needed_work),
                "pending_review_count": len(review_queue) if traces else len(review_needed_work),
                "total_source_spans": total_source_spans,
            },
            "dataset_context": dataset_context,
            "raw_trace_examples": raw_trace_examples,
            "normalized_observation_examples": normalized_observation_examples,
            "work_unit_examples": work_unit_examples,
            "review_needed_work": review_needed_work,
            "cost_by_work_category": sorted(
                (
                    {
                        "work_category": key,
                        "blended_cost": round(value["blended_cost"], 6),
                        "work_units": value["work_units"],
                    }
                    for key, value in category_totals.items()
                ),
                key=lambda item: item["blended_cost"],
                reverse=True,
            ),
            "cost_by_trust_state": sorted(
                (
                    {
                        "trust_state": key,
                        "blended_cost": round(value["blended_cost"], 6),
                        "work_units": value["work_units"],
                    }
                    for key, value in trust_totals.items()
                ),
                key=lambda item: item["blended_cost"],
                reverse=True,
            ),
            "cost_by_policy_outcome": sorted(
                (
                    {
                        "policy_outcome": key,
                        "blended_cost": round(value["blended_cost"], 6),
                        "work_units": value["work_units"],
                    }
                    for key, value in policy_outcome_totals.items()
                ),
                key=lambda item: item["blended_cost"],
                reverse=True,
            ),
            "pending_review_queue": review_queue,
            "top_ambiguous_items": top_ambiguous_items,
            "low_trust_high_cost": sorted(
                low_trust_high_cost, key=lambda item: item["blended_cost"], reverse=True
            ),
            "top_material_work_units": top_material_work_units,
            "compression_story": {
                "total_source_spans": total_source_spans,
                "avg_source_spans_per_work_unit": round(
                    total_source_spans / len(work_units), 2
                )
                if work_units
                else 0.0,
                "avg_compression_ratio": avg_compression_ratio,
                "max_compression_ratio": max(
                    (item.compression_ratio for item in work_units), default=0.0
                ),
                "proof_point": compression_proof_point,
            },
        }
        if include_economics and spans:
            summary["comparative_economics"] = build_comparative_economics(
                spans,
                work_units,
                traces,
                [
                    scenario_presets()["open_hosted"],
                    scenario_presets()["self_hosted_gpu"],
                ],
            )
        return summary

    def render_terminal(self, console: Console | None = None) -> None:
        console = console or Console()
        summary = self.summary()
        totals = summary["totals"]
        totals_table = Table(title="workledger summary")
        totals_table.add_column("metric")
        totals_table.add_column("value", justify="right")
        for label, value in totals.items():
            totals_table.add_row(label, str(value))
        console.print(totals_table)

        if summary["dataset_context"]:
            dataset_table = Table(title="dataset context")
            dataset_table.add_column("dataset")
            dataset_table.add_column("split")
            dataset_table.add_column("adapter")
            dataset_table.add_column("rows", justify="right")
            dataset_table.add_column("traces", justify="right")
            dataset_table.add_column("observations", justify="right")
            for row in summary["dataset_context"]:
                dataset_table.add_row(
                    row["dataset_id"],
                    row["split"],
                    row["adapter"],
                    str(row["row_count"]),
                    str(row["trace_count"]),
                    str(row["observation_count"]),
                )
            console.print(dataset_table)

        work_table = Table(title="rolled work units")
        work_table.add_column("title")
        work_table.add_column("kind")
        work_table.add_column("review")
        work_table.add_column("evidence", justify="right")
        work_table.add_column("spans", justify="right")
        work_table.add_column("cost", justify="right")
        for row in summary["work_unit_examples"][:10]:
            work_table.add_row(
                row["title"],
                row["kind"],
                row["review_state"],
                str(row["evidence_count"]),
                str(row["source_span_count"]),
                f"${row['total_cost']:.4f}",
            )
        console.print(work_table)

        if summary["review_needed_work"]:
            review_table = Table(title="review-needed work")
            review_table.add_column("title")
            review_table.add_column("kind")
            review_table.add_column("review")
            review_table.add_column("reason")
            review_table.add_column("spans", justify="right")
            for row in summary["review_needed_work"]:
                review_table.add_row(
                    row["title"],
                    row["kind"],
                    row["review_state"],
                    row["reason"],
                    str(row["source_span_count"]),
                )
            console.print(review_table)

        if summary["cost_by_policy_outcome"]:
            cap_table = Table(title="cost by policy outcome")
            cap_table.add_column("policy outcome")
            cap_table.add_column("blended cost", justify="right")
            cap_table.add_column("work units", justify="right")
            for row in summary["cost_by_policy_outcome"]:
                cap_table.add_row(
                    row["policy_outcome"], f"${row['blended_cost']:.4f}", str(row["work_units"])
                )
            console.print(cap_table)

        if summary["pending_review_queue"]:
            queue_table = Table(title="pending review queue")
            queue_table.add_column("title")
            queue_table.add_column("category")
            queue_table.add_column("outcome")
            queue_table.add_column("cost", justify="right")
            queue_table.add_column("confidence", justify="right")
            queue_table.add_column("spans", justify="right")
            queue_table.add_column("compression", justify="right")
            for row in summary["pending_review_queue"]:
                queue_table.add_row(
                    row["title"],
                    row["work_category"],
                    row["policy_outcome"],
                    f"${row['blended_cost']:.4f}",
                    f"{row['confidence_score']:.2f}",
                    str(row["source_span_count"]),
                    f"{row['compression_ratio']:.2f}x",
                )
            console.print(queue_table)

        if summary["low_trust_high_cost"]:
            risk_table = Table(title="low-trust high-cost outputs")
            risk_table.add_column("title")
            risk_table.add_column("category")
            risk_table.add_column("cost", justify="right")
            risk_table.add_column("trust")
            for row in summary["low_trust_high_cost"]:
                risk_table.add_row(
                    row["title"],
                    row["work_category"],
                    f"${row['blended_cost']:.4f}",
                    row["trust_state"],
                )
            console.print(risk_table)

    def write_report_bundle(
        self,
        reports_dir: Path,
        *,
        include_economics: bool = False,
    ) -> list[ReportArtifact]:
        reports_dir.mkdir(parents=True, exist_ok=True)
        summary = self.summary(include_economics=include_economics)

        json_path = reports_dir / "summary.json"
        json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        csv_path = reports_dir / "cost_by_work_category.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=["work_category", "blended_cost", "work_units"]
            )
            writer.writeheader()
            writer.writerows(summary["cost_by_work_category"])

        parquet_path = reports_dir / "classification_traces.parquet"
        self.store.export_table("classification_traces", parquet_path, "parquet")

        markdown_path = reports_dir / "summary.md"
        markdown_path.write_text(self._render_markdown(summary), encoding="utf-8")

        html_path = reports_dir / "summary.html"
        html_path.write_text(self._render_html(summary), encoding="utf-8")

        artifacts = [
            ReportArtifact(
                report_kind="json_summary", uri=str(json_path), content_type="application/json"
            ),
            ReportArtifact(
                report_kind="csv_cost_by_category", uri=str(csv_path), content_type="text/csv"
            ),
            ReportArtifact(
                report_kind="parquet_classifications",
                uri=str(parquet_path),
                content_type="application/x-parquet",
            ),
            ReportArtifact(
                report_kind="markdown_summary", uri=str(markdown_path), content_type="text/markdown"
            ),
            ReportArtifact(
                report_kind="html_summary", uri=str(html_path), content_type="text/html"
            ),
        ]
        for artifact in artifacts:
            self.store.save_report(artifact)
        return artifacts

    def _render_markdown(self, summary: dict[str, Any]) -> str:
        proof_point = summary["compression_story"]["proof_point"]
        lines = [
            "# workledger report",
            "",
            "Observability tells you what ran. workledger tells you what work happened.",
            "",
            "## Totals",
            "",
        ]
        for key, value in summary["totals"].items():
            lines.append(f"- **{key}**: {value}")

        lines.extend(["", "## Dataset Context", ""])
        if summary["dataset_context"]:
            lines.extend(
                [
                    "| dataset | split | adapter | rows | traces | observations |",
                    "| --- | --- | --- | ---: | ---: | ---: |",
                ]
            )
            for row in summary["dataset_context"]:
                lines.append(
                    f"| {row['dataset_id']} | {row['split']} | {row['adapter']} | {row['row_count']} | {row['trace_count']} | {row['observation_count']} |"
                )
        else:
            lines.append("- No Hugging Face dataset context detected.")

        lines.extend(["", "## Raw Trace Excerpt", ""])
        if summary["raw_trace_examples"]:
            for row in summary["raw_trace_examples"]:
                lines.append(
                    f"- **{row['title']}** (`{row['trace_id']}`) from {row['source_ref']} with {row['step_count']} raw steps"
                )
                if row["steps"]:
                    lines.append(f"  steps: {' -> '.join(row['steps'])}")
        else:
            lines.append("- No trace excerpts available.")

        lines.extend(
            [
                "",
                "## Normalized Observations",
                "",
                "| trace | span | kind | name | source ref |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for row in summary["normalized_observation_examples"] or [
            {"trace_id": "-", "span_id": "-", "span_kind": "-", "name": "-", "raw_payload_ref": "-"}
        ]:
            lines.append(
                f"| {row['trace_id']} | {row['span_id']} | {row['span_kind']} | {row['name']} | {row['raw_payload_ref']} |"
            )

        lines.extend(
            [
                "",
                "## Rolled Work Units",
                "",
                "| title | kind | review | trust | evidence | spans | total cost |",
                "| --- | --- | --- | --- | ---: | ---: | ---: |",
            ]
        )
        for row in summary["work_unit_examples"] or [
            {
                "title": "none",
                "kind": "-",
                "review_state": "-",
                "trust_state": "-",
                "evidence_count": 0,
                "source_span_count": 0,
                "total_cost": 0.0,
            }
        ]:
            lines.append(
                f"| {row['title']} | {row['kind']} | {row['review_state']} | {row['trust_state']} | {row['evidence_count']} | {row['source_span_count']} | ${row['total_cost']:.4f} |"
            )

        lines.extend(
            [
                "",
                "## Review-Needed Work",
                "",
                "| title | kind | review | reason | spans | evidence |",
                "| --- | --- | --- | --- | ---: | ---: |",
            ]
        )
        for row in summary["review_needed_work"] or [
            {
                "title": "none",
                "kind": "-",
                "review_state": "-",
                "reason": "-",
                "source_span_count": 0,
                "evidence_count": 0,
            }
        ]:
            lines.append(
                f"| {row['title']} | {row['kind']} | {row['review_state']} | {row['reason']} | {row['source_span_count']} | {row['evidence_count']} |"
            )

        lines.extend(
            [
                "",
                "## Cost by Policy Outcome",
                "",
                "| policy outcome | blended cost | work units |",
                "| --- | ---: | ---: |",
            ]
        )
        for row in summary["cost_by_policy_outcome"] or [
            {"policy_outcome": "none", "blended_cost": 0, "work_units": 0}
        ]:
            lines.append(
                f"| {row['policy_outcome']} | {row['blended_cost']:.4f} | {row['work_units']} |"
            )

        lines.extend(
            [
                "",
                "## Pending Review Queue",
                "",
                "| title | category | outcome | cost | confidence | spans | compression | competing |",
                "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for row in summary["pending_review_queue"] or [
            {
                "title": "none",
                "work_category": "-",
                "policy_outcome": "-",
                "blended_cost": 0.0,
                "confidence_score": 0.0,
                "source_span_count": 0,
                "compression_ratio": 0.0,
                "competing_candidates": [],
            }
        ]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        row["title"],
                        row["work_category"],
                        row["policy_outcome"],
                        f"${row['blended_cost']:.4f}",
                        f"{row['confidence_score']:.2f}",
                        str(row["source_span_count"]),
                        f"{row['compression_ratio']:.2f}x",
                        _format_candidates(row["competing_candidates"]),
                    ]
                )
                + " |"
            )

        lines.extend(["", "## Top Ambiguous Items", ""])
        for row in summary["top_ambiguous_items"] or [
            {"title": "none", "work_category": "-", "confidence_score": 0.0, "confidence_gap": None}
        ]:
            gap = "-" if row["confidence_gap"] is None else f"{row['confidence_gap']:.2f}"
            lines.append(
                f"- {row['title']} | {row['work_category']} | confidence {row['confidence_score']:.2f} | gap {gap}"
            )

        lines.extend(
            [
                "",
                "## Compression Proof Point",
                "",
                (
                    f"- {proof_point['title']} | {proof_point['source_span_count']} source spans | {proof_point['compression_ratio']:.2f}x compression"
                    if proof_point
                    else "- none"
                ),
                "",
                "## Low-Trust High-Cost Outputs",
                "",
            ]
        )
        for row in summary["low_trust_high_cost"] or [
            {"title": "none", "work_category": "-", "blended_cost": 0, "trust_state": "-"}
        ]:
            lines.append(
                f"- {row['title']} | {row['work_category']} | ${row['blended_cost']:.4f} | {row['trust_state']}"
            )

        comparative = summary.get("comparative_economics")
        if comparative:
            lines.extend(
                [
                    "",
                    "## Comparative Economics",
                    "",
                    "| scenario | estimated cost | savings vs observed | savings % |",
                    "| --- | ---: | ---: | ---: |",
                ]
            )
            for row in comparative["comparisons"]:
                lines.append(
                    f"| {row['label']} | ${row['total_cost']:.4f} | ${row['savings_delta']:.4f} | {row['savings_percent']:.2f}% |"
                )
            lines.extend(["", "### Caveats", ""])
            for caveat in comparative["caveats"]:
                lines.append(f"- {caveat}")
        return "\n".join(lines) + "\n"

    def _render_html(self, summary: dict[str, Any]) -> str:
        dataset_rows = "".join(
            f"<tr><td>{escape(row['dataset_id'])}</td><td>{escape(row['split'])}</td><td>{escape(row['adapter'])}</td><td>{row['row_count']}</td><td>{row['trace_count']}</td><td>{row['observation_count']}</td></tr>"
            for row in summary["dataset_context"]
        ) or "<tr><td colspan='6'>No Hugging Face dataset context detected</td></tr>"
        raw_trace_rows = "".join(
            f"<tr><td>{escape(row['title'])}</td><td>{escape(row['trace_id'])}</td><td>{row['step_count']}</td><td>{escape(' -> '.join(row['steps']))}</td><td>{escape(row['source_ref'])}</td></tr>"
            for row in summary["raw_trace_examples"]
        ) or "<tr><td colspan='5'>No trace excerpts available</td></tr>"
        observation_rows = "".join(
            f"<tr><td>{escape(row['trace_id'])}</td><td>{escape(row['span_id'])}</td><td>{escape(row['span_kind'])}</td><td>{escape(row['name'])}</td><td>{escape(row['raw_payload_ref'])}</td></tr>"
            for row in summary["normalized_observation_examples"]
        ) or "<tr><td colspan='5'>No observations available</td></tr>"
        work_rows = "".join(
            f"<tr><td>{escape(row['title'])}</td><td>{escape(row['kind'])}</td><td>{escape(row['review_state'])}</td><td>{escape(row['trust_state'])}</td><td>{row['evidence_count']}</td><td>{row['source_span_count']}</td><td>${row['total_cost']:.4f}</td></tr>"
            for row in summary["work_unit_examples"]
        ) or "<tr><td colspan='7'>No work units available</td></tr>"
        review_work_rows = "".join(
            f"<tr><td>{escape(row['title'])}</td><td>{escape(row['kind'])}</td><td>{escape(row['review_state'])}</td><td>{escape(row['reason'])}</td><td>{row['source_span_count']}</td><td>{row['evidence_count']}</td></tr>"
            for row in summary["review_needed_work"]
        ) or "<tr><td colspan='6'>No review-needed work items</td></tr>"
        outcome_rows = "".join(
            f"<tr><td>{escape(row['policy_outcome'])}</td><td>${row['blended_cost']:.4f}</td><td>{row['work_units']}</td></tr>"
            for row in summary["cost_by_policy_outcome"]
        ) or "<tr><td colspan='3'>No policy outcome totals available</td></tr>"
        queue_rows = "".join(
            (
                f"<tr><td>{escape(row['title'])}</td><td>{escape(row['work_category'])}</td>"
                f"<td>{escape(row['policy_outcome'])}</td><td>${row['blended_cost']:.4f}</td>"
                f"<td>{row['confidence_score']:.2f}</td><td>{row['source_span_count']}</td>"
                f"<td>{row['compression_ratio']:.2f}x</td>"
                f"<td>{escape(_format_candidates(row['competing_candidates']))}</td></tr>"
            )
            for row in summary["pending_review_queue"]
        ) or "<tr><td colspan='8'>No pending review items</td></tr>"
        ambiguous_rows = "".join(
            f"<tr><td>{escape(row['title'])}</td><td>{escape(row['work_category'])}</td><td>{row['confidence_score']:.2f}</td><td>{_format_gap(row['confidence_gap'])}</td></tr>"
            for row in summary["top_ambiguous_items"]
        ) or "<tr><td colspan='4'>No ambiguous items</td></tr>"
        risk_rows = "".join(
            f"<tr><td>{escape(row['title'])}</td><td>{escape(row['work_category'])}</td><td>${row['blended_cost']:.4f}</td><td>{escape(row['trust_state'])}</td></tr>"
            for row in summary["low_trust_high_cost"]
        ) or "<tr><td colspan='4'>No low-trust high-cost outputs</td></tr>"
        total_cards = "".join(
            f"<div class='card'><div class='label'>{escape(key)}</div><div class='value'>{value}</div></div>"
            for key, value in summary["totals"].items()
        )
        proof_point = summary["compression_story"]["proof_point"]
        proof_markup = (
            f"<p><strong>{escape(proof_point['title'])}</strong> condensed {proof_point['source_span_count']} source spans into a {proof_point['compression_ratio']:.2f}x business work signal.</p>"
            if proof_point
            else "<p>No compression proof point is available.</p>"
        )
        comparative = summary.get("comparative_economics")
        comparative_markup = ""
        if comparative:
            comparative_rows = "".join(
                f"<tr><td>{escape(row['label'])}</td><td>${row['total_cost']:.4f}</td><td>${row['savings_delta']:.4f}</td><td>{row['savings_percent']:.2f}%</td></tr>"
                for row in comparative["comparisons"]
            )
            comparative_caveats = "".join(
                f"<li>{escape(item)}</li>" for item in comparative["caveats"]
            )
            comparative_markup = f"""
      <section>
        <h2>Comparative Economics</h2>
        <table>
          <thead><tr><th>Scenario</th><th>Estimated cost</th><th>Savings delta</th><th>Savings %</th></tr></thead>
          <tbody>{comparative_rows}</tbody>
        </table>
        <ul>{comparative_caveats}</ul>
      </section>"""
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>workledger report</title>
    <style>
      :root {{
        --bg: #f2efe8;
        --ink: #1e2430;
        --accent: #0f766e;
        --panel: #fffdf8;
        --muted: #6b7280;
        --border: #d9d2c3;
      }}
      body {{
        margin: 0;
        font-family: "Iowan Old Style", "Palatino Linotype", serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top right, rgba(15, 118, 110, 0.16), transparent 34%),
          linear-gradient(180deg, #f8f5ef 0%, var(--bg) 100%);
      }}
      main {{
        max-width: 1120px;
        margin: 0 auto;
        padding: 48px 24px 72px;
      }}
      h1 {{
        font-size: 3rem;
        margin-bottom: 0.5rem;
      }}
      .hero {{
        display: grid;
        gap: 8px;
        margin-bottom: 24px;
      }}
      .hero strong {{
        color: var(--accent);
        font-size: 1.05rem;
        letter-spacing: 0.02em;
      }}
      .sub {{
        color: var(--muted);
        max-width: 58rem;
        margin-bottom: 0;
      }}
      .cards {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 16px;
        margin-bottom: 32px;
      }}
      .card, section {{
        background: rgba(255, 253, 248, 0.88);
        border: 1px solid var(--border);
        border-radius: 18px;
        box-shadow: 0 10px 28px rgba(30, 36, 48, 0.06);
      }}
      .card {{
        padding: 20px;
      }}
      .label {{
        color: var(--muted);
        font-size: 0.86rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }}
      .value {{
        font-size: 1.8rem;
        margin-top: 8px;
      }}
      section {{
        padding: 20px 24px;
        margin-bottom: 24px;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
      }}
      td, th {{
        padding: 12px 8px;
        border-bottom: 1px solid var(--border);
        text-align: left;
        vertical-align: top;
      }}
      th {{
        color: var(--muted);
        font-size: 0.84rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }}
    </style>
  </head>
  <body>
    <main>
      <h1>workledger</h1>
      <div class="hero">
        <strong>Observability tells you what ran. workledger tells you what work happened.</strong>
        <p class="sub">This report turns raw traces into normalized observations, rolled work units, and explicit review-needed work. Policy and economics remain downstream views.</p>
      </div>
      <div class="cards">{total_cards}</div>
      <section>
        <h2>Dataset Context</h2>
        <table>
          <thead><tr><th>Dataset</th><th>Split</th><th>Adapter</th><th>Rows</th><th>Traces</th><th>Observations</th></tr></thead>
          <tbody>{dataset_rows}</tbody>
        </table>
      </section>
      <section>
        <h2>Raw Trace Excerpt</h2>
        <table>
          <thead><tr><th>Title</th><th>Trace</th><th>Steps</th><th>Excerpt</th><th>Source ref</th></tr></thead>
          <tbody>{raw_trace_rows}</tbody>
        </table>
      </section>
      <section>
        <h2>Normalized Observations</h2>
        <table>
          <thead><tr><th>Trace</th><th>Span</th><th>Kind</th><th>Name</th><th>Source ref</th></tr></thead>
          <tbody>{observation_rows}</tbody>
        </table>
      </section>
      <section>
        <h2>Rolled Work Units</h2>
        <table>
          <thead><tr><th>Title</th><th>Kind</th><th>Review</th><th>Trust</th><th>Evidence</th><th>Spans</th><th>Total cost</th></tr></thead>
          <tbody>{work_rows}</tbody>
        </table>
      </section>
      <section>
        <h2>Review-Needed Work</h2>
        <table>
          <thead><tr><th>Title</th><th>Kind</th><th>Review</th><th>Reason</th><th>Spans</th><th>Evidence</th></tr></thead>
          <tbody>{review_work_rows}</tbody>
        </table>
      </section>
      <section>
        <h2>Cost by Policy Outcome</h2>
        <table>
          <thead><tr><th>Policy outcome</th><th>Blended cost</th><th>Work units</th></tr></thead>
          <tbody>{outcome_rows}</tbody>
        </table>
      </section>
      <section>
        <h2>Pending Review Queue</h2>
        <table>
          <thead><tr><th>Title</th><th>Category</th><th>Outcome</th><th>Cost</th><th>Confidence</th><th>Spans</th><th>Compression</th><th>Competing</th></tr></thead>
          <tbody>{queue_rows}</tbody>
        </table>
      </section>
      <section>
        <h2>Compression Proof Point</h2>
        {proof_markup}
      </section>
      <section>
        <h2>Top Ambiguous Items</h2>
        <table>
          <thead><tr><th>Title</th><th>Category</th><th>Confidence</th><th>Gap</th></tr></thead>
          <tbody>{ambiguous_rows}</tbody>
        </table>
      </section>
      <section>
        <h2>Low-Trust High-Cost Outputs</h2>
        <table>
          <thead><tr><th>Title</th><th>Category</th><th>Cost</th><th>Trust</th></tr></thead>
          <tbody>{risk_rows}</tbody>
        </table>
      </section>{comparative_markup}
    </main>
  </body>
</html>
"""

    def _dataset_context(self, spans: list[ObservationSpan]) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
        for span in spans:
            hf = span.facets.get("hf")
            if not isinstance(hf, dict):
                continue
            dataset_id = str(hf.get("dataset_id", "unknown"))
            split = str(hf.get("split", "train"))
            adapter = str(hf.get("adapter", "unknown"))
            key = (dataset_id, split, adapter)
            bucket = grouped.setdefault(
                key,
                {
                    "dataset_id": dataset_id,
                    "split": split,
                    "adapter": adapter,
                    "row_indexes": set(),
                    "trace_ids": set(),
                    "observation_count": 0,
                },
            )
            row_index = hf.get("row_index")
            if row_index is not None:
                bucket["row_indexes"].add(int(row_index))
            bucket["trace_ids"].add(span.trace_id)
            bucket["observation_count"] += 1
        return [
            {
                "dataset_id": item["dataset_id"],
                "split": item["split"],
                "adapter": item["adapter"],
                "row_count": len(item["row_indexes"]),
                "trace_count": len(item["trace_ids"]),
                "observation_count": item["observation_count"],
            }
            for item in grouped.values()
        ]

    def _raw_trace_examples(self, spans: list[ObservationSpan]) -> list[dict[str, Any]]:
        grouped: dict[str, list[ObservationSpan]] = defaultdict(list)
        for span in spans:
            grouped[span.trace_id].append(span)
        examples: list[dict[str, Any]] = []
        for trace_id, trace_spans in list(grouped.items())[:5]:
            ordered = sorted(trace_spans, key=lambda item: item.start_time)
            title = ordered[0].attributes.get("task_title") or ordered[0].name
            examples.append(
                {
                    "trace_id": trace_id,
                    "title": str(title),
                    "step_count": len(ordered),
                    "steps": [span.name for span in ordered[:5]],
                    "source_ref": ordered[0].raw_payload_ref or f"trace:{trace_id}",
                }
            )
        return examples

    def _normalized_observation_examples(
        self, spans: list[ObservationSpan]
    ) -> list[dict[str, Any]]:
        return [
            {
                "trace_id": span.trace_id,
                "span_id": span.span_id,
                "span_kind": str(span.span_kind),
                "name": span.name,
                "raw_payload_ref": span.raw_payload_ref or "-",
            }
            for span in spans[:8]
        ]

    def _work_unit_examples(self, work_units: list[WorkUnit]) -> list[dict[str, Any]]:
        ordered = sorted(
            work_units,
            key=lambda item: (item.importance_score, item.total_cost, item.compression_ratio),
            reverse=True,
        )
        return [
            {
                "work_unit_id": item.work_unit_id,
                "title": item.title,
                "kind": item.kind,
                "review_state": str(item.review_state),
                "trust_state": str(item.trust_state),
                "evidence_count": len(item.evidence_bundle),
                "source_span_count": len(item.source_span_ids),
                "compression_ratio": item.compression_ratio,
                "total_cost": item.total_cost,
                "duration_ms": item.duration_ms,
            }
            for item in ordered[:10]
        ]

    def _review_needed_work(
        self, work_units: list[WorkUnit], traces: list[ClassificationTrace]
    ) -> list[dict[str, Any]]:
        trace_by_work_unit = {trace.work_unit_id: trace for trace in traces}
        items: list[dict[str, Any]] = []
        for work_unit in work_units:
            trace = trace_by_work_unit.get(work_unit.work_unit_id)
            review_state = str(work_unit.review_state)
            if review_state != "queued" and not (trace and trace.reviewer_required):
                continue
            reason = "queued during trace-to-work rollup"
            if trace and trace.reviewer_required:
                reason = "policy classification still requires review"
            items.append(
                {
                    "work_unit_id": work_unit.work_unit_id,
                    "title": work_unit.title,
                    "kind": work_unit.kind,
                    "review_state": review_state,
                    "reason": reason,
                    "source_span_count": len(work_unit.source_span_ids),
                    "evidence_count": len(work_unit.evidence_bundle),
                }
            )
        return items
