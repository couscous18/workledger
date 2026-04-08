from __future__ import annotations

from dataclasses import dataclass

from workledger.models import ObservationSpan


@dataclass(slots=True)
class GitContext:
    repository: str
    branch: str
    files_touched: list[str]
    issue_labels: list[str]
    pr_number: str | None = None
    diff_stats: dict[str, int] | None = None
    deployment_target: str | None = None


def enrich_spans_with_git_context(
    spans: list[ObservationSpan], context: GitContext
) -> list[ObservationSpan]:
    enriched: list[ObservationSpan] = []
    for span in spans:
        attributes = dict(span.attributes)
        facets = dict(span.facets)
        facets["git"] = {
            "repository": context.repository,
            "branch": context.branch,
            "files_touched": context.files_touched,
            "issue_labels": context.issue_labels,
            "pr_number": context.pr_number,
            "diff_stats": context.diff_stats or {},
            "deployment_target": context.deployment_target,
        }
        if context.issue_labels:
            attributes["issue_labels"] = context.issue_labels
        enriched.append(span.model_copy(update={"attributes": attributes, "facets": facets}))
    return enriched
