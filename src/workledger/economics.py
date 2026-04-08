from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from workledger.models import ClassificationTrace, ObservationSpan, WorkUnit

CAVEATS = [
    "Estimates are assumption-driven and do not measure model quality or task success.",
    "Self-hosted totals are sensitive to utilization, batching, and infrastructure overhead.",
    "Latency, eval cost, on-call burden, and GPU reservation waste are excluded unless modeled as overhead.",
]


@dataclass(frozen=True)
class CostScenario:
    name: str
    label: str
    input_cost_per_1m: float
    output_cost_per_1m: float
    fixed_overhead: float = 0.0
    description: str = ""


def scenario_presets() -> dict[str, CostScenario]:
    return {
        "proprietary_api": CostScenario(
            name="proprietary_api",
            label="Proprietary API",
            input_cost_per_1m=5.0,
            output_cost_per_1m=15.0,
            description="Illustrative API pricing for a premium hosted model.",
        ),
        "open_hosted": CostScenario(
            name="open_hosted",
            label="Open Hosted",
            input_cost_per_1m=0.8,
            output_cost_per_1m=2.4,
            description="Illustrative pricing for hosted open-weight inference.",
        ),
        "self_hosted_gpu": CostScenario(
            name="self_hosted_gpu",
            label="Self-Hosted GPU",
            input_cost_per_1m=0.35,
            output_cost_per_1m=0.9,
            fixed_overhead=1.25,
            description="Illustrative effective token cost plus a modest fixed infra overhead.",
        ),
    }


def _estimate_cost(tokens_in: int, tokens_out: int, scenario: CostScenario) -> dict[str, float]:
    input_cost = (tokens_in / 1_000_000) * scenario.input_cost_per_1m
    output_cost = (tokens_out / 1_000_000) * scenario.output_cost_per_1m
    variable_cost = input_cost + output_cost
    total_cost = variable_cost + scenario.fixed_overhead
    total_tokens = max(tokens_in + tokens_out, 1)
    return {
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "variable_cost": round(variable_cost, 6),
        "fixed_overhead": round(scenario.fixed_overhead, 6),
        "total_cost": round(total_cost, 6),
        "cost_per_1k_tokens": round((total_cost / total_tokens) * 1000, 6),
        "cost_per_1m_tokens": round((total_cost / total_tokens) * 1_000_000, 6),
    }


def build_comparative_economics(
    spans: list[ObservationSpan],
    work_units: list[WorkUnit],
    traces: list[ClassificationTrace],
    scenarios: list[CostScenario],
) -> dict[str, Any]:
    if not spans or not scenarios:
        return {}

    total_input_tokens = sum(span.token_input for span in spans)
    total_output_tokens = sum(span.token_output for span in spans)
    total_tokens = total_input_tokens + total_output_tokens
    observed_direct_cost = round(sum(span.direct_cost for span in spans), 6)
    work_unit_by_id = {item.work_unit_id: item for item in work_units}
    span_by_id = {span.span_id: span for span in spans}

    comparisons: list[dict[str, Any]] = []
    category_breakdown: list[dict[str, Any]] = []
    baseline_total = observed_direct_cost

    for scenario in scenarios:
        estimate = _estimate_cost(total_input_tokens, total_output_tokens, scenario)
        delta = round(baseline_total - estimate["total_cost"], 6)
        savings_pct = round((delta / baseline_total) * 100, 2) if baseline_total else 0.0
        comparisons.append(
            {
                "scenario": scenario.name,
                "label": scenario.label,
                "description": scenario.description,
                "input_cost_per_1m": scenario.input_cost_per_1m,
                "output_cost_per_1m": scenario.output_cost_per_1m,
                "fixed_overhead": scenario.fixed_overhead,
                **estimate,
                "observed_cost": baseline_total,
                "savings_delta": delta,
                "savings_percent": savings_pct,
            }
        )

    if traces:
        for trace in traces:
            work_unit = work_unit_by_id.get(trace.work_unit_id)
            if work_unit is None:
                continue
            category_spans = [span_by_id[span_id] for span_id in work_unit.source_span_ids if span_id in span_by_id]
            input_tokens = sum(span.token_input for span in category_spans)
            output_tokens = sum(span.token_output for span in category_spans)
            observed_cost = round(sum(span.direct_cost for span in category_spans), 6)
            scenario_rows = []
            for scenario in scenarios:
                estimate = _estimate_cost(input_tokens, output_tokens, scenario)
                scenario_rows.append(
                    {
                        "scenario": scenario.name,
                        "label": scenario.label,
                        "estimated_cost": estimate["total_cost"],
                        "savings_delta": round(observed_cost - estimate["total_cost"], 6),
                    }
                )
            category_breakdown.append(
                {
                    "work_unit_id": trace.work_unit_id,
                    "title": work_unit.title,
                    "work_category": str(trace.work_category),
                    "policy_outcome": str(trace.policy_outcome),
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "observed_cost": observed_cost,
                    "scenarios": scenario_rows,
                }
            )

    return {
        "observed": {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "total_tokens": total_tokens,
            "observed_direct_cost": observed_direct_cost,
            "work_unit_count": len(work_units),
            "classification_count": len(traces),
        },
        "comparisons": comparisons,
        "category_breakdown": category_breakdown,
        "caveats": CAVEATS,
    }
