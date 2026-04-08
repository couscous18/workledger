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
from workledger.models import ReportArtifact
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

        total_direct_cost = round(sum(trace.direct_cost for trace in traces), 6)
        total_blended_cost = round(sum(trace.blended_cost for trace in traces), 6)
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
                "review_burden": sum(1 for trace in traces if trace.reviewer_required),
                "pending_review_count": len(review_queue),
                "total_source_spans": total_source_spans,
            },
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

        cost_table = Table(title="cost by work category")
        cost_table.add_column("work category")
        cost_table.add_column("blended cost", justify="right")
        cost_table.add_column("work units", justify="right")
        for row in summary["cost_by_work_category"]:
            cost_table.add_row(
                row["work_category"], f"${row['blended_cost']:.4f}", str(row["work_units"])
            )
        console.print(cost_table)

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
            "## Totals",
            "",
        ]
        for key, value in summary["totals"].items():
            lines.append(f"- **{key}**: {value}")
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
        lines.extend(
            [
                "",
                "## Top Ambiguous Items",
                "",
            ]
        )
        for row in summary["top_ambiguous_items"] or [
            {"title": "none", "work_category": "-", "confidence_score": 0.0, "confidence_gap": None}
        ]:
            gap = "-" if row["confidence_gap"] is None else f"{row['confidence_gap']:.2f}"
            lines.append(
                f"- {row['title']} | {row['work_category']} | "
                f"confidence {row['confidence_score']:.2f} | gap {gap}"
            )
        lines.extend(
            [
                "",
                "## Compression Proof Point",
                "",
                (
                    f"- {proof_point['title']} | {proof_point['source_span_count']} source spans | "
                    f"{proof_point['compression_ratio']:.2f}x compression"
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
        category_rows = "".join(
            f"<tr><td>{escape(row['work_category'])}</td><td>${row['blended_cost']:.4f}</td><td>{row['work_units']}</td></tr>"
            for row in summary["cost_by_work_category"]
        )
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
            f"<tr><td>{escape(row['title'])}</td><td>{escape(row['work_category'])}</td>"
            f"<td>{row['confidence_score']:.2f}</td>"
            f"<td>{_format_gap(row['confidence_gap'])}</td></tr>"
            for row in summary["top_ambiguous_items"]
        ) or "<tr><td colspan='4'>No ambiguous items</td></tr>"
        risk_rows = (
            "".join(
                f"<tr><td>{escape(row['title'])}</td><td>{escape(row['work_category'])}</td><td>${row['blended_cost']:.4f}</td><td>{escape(row['trust_state'])}</td></tr>"
                for row in summary["low_trust_high_cost"]
            )
            or "<tr><td colspan='4'>No low-trust high-cost outputs</td></tr>"
        )
        total_cards = "".join(
            f"<div class='card'><div class='label'>{escape(key)}</div><div class='value'>{value}</div></div>"
            for key, value in summary["totals"].items()
        )
        proof_point = summary["compression_story"]["proof_point"]
        proof_markup = (
            f"<p><strong>{escape(proof_point['title'])}</strong> condensed "
            f"{proof_point['source_span_count']} source spans into a {proof_point['compression_ratio']:.2f}x business work signal.</p>"
            if proof_point
            else "<p>No compression proof point is available.</p>"
        )
        comparative = summary.get("comparative_economics")
        comparative_rows = ""
        comparative_caveats = ""
        if comparative:
            comparative_rows = "".join(
                f"<tr><td>{escape(row['label'])}</td><td>${row['total_cost']:.4f}</td><td>${row['savings_delta']:.4f}</td><td>{row['savings_percent']:.2f}%</td></tr>"
                for row in comparative["comparisons"]
            )
            comparative_caveats = "".join(
                f"<li>{escape(item)}</li>" for item in comparative["caveats"]
            )
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
      .sub {{
        color: var(--muted);
        max-width: 58rem;
        margin-bottom: 2rem;
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
      <p class="sub">This report summarizes work unit classifications, review burden, and the compression from raw spans to reviewable work units.</p>
      <div class="cards">{total_cards}</div>
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
        <h2>Cost by Work Category</h2>
        <table>
          <thead><tr><th>Work category</th><th>Blended cost</th><th>Work units</th></tr></thead>
          <tbody>{category_rows}</tbody>
        </table>
      </section>
      <section>
        <h2>Low-Trust High-Cost Outputs</h2>
        <table>
          <thead><tr><th>Title</th><th>Category</th><th>Cost</th><th>Trust</th></tr></thead>
          <tbody>{risk_rows}</tbody>
        </table>
      </section>
      {f'''
      <section>
        <h2>Comparative Economics</h2>
        <table>
          <thead><tr><th>Scenario</th><th>Estimated cost</th><th>Savings vs observed</th><th>Savings %</th></tr></thead>
          <tbody>{comparative_rows}</tbody>
        </table>
        <ul>{comparative_caveats}</ul>
      </section>
      ''' if comparative else ''}
    </main>
  </body>
</html>
"""
