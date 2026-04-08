from __future__ import annotations

from pathlib import Path

BUILTIN_POLICY_PACKS: dict[str, str] = {
    "management_reporting_v1.yaml": """policy_pack_id: management_reporting_v1
version: 1.0.0
basis: management_reporting_v1
title: Management Reporting
description: Pragmatic management reporting policy pack for turning AI work into reviewable work categories and outcomes.
default_work_category: general_admin
default_policy_outcome: review_required
rules:
  - id: marketing_campaign_output
    priority: 100
    when:
      any:
        - feature: marketing.channel
          op: exists
        - feature: labels
          op: overlaps
          value: ["marketing", "campaign"]
        - feature: kind
          op: eq
          value: marketing_generation
    decision:
      work_category: advertising_marketing
      policy_outcome: expense_now
      cost_category: marketing_generation
      confidence: 0.94
    explanation: Campaign metadata, channel metadata, or marketing labels indicate advertising and marketing work.

  - id: support_resolution
    priority: 95
    when:
      any:
        - feature: support.ticket_id
          op: exists
        - feature: labels
          op: overlaps
          value: ["support", "customer"]
        - feature: kind
          op: eq
          value: support_resolution
    decision:
      work_category: support_service_delivery
      policy_outcome: expense_now
      cost_category: support_automation
      confidence: 0.91
    explanation: Ticket linkage and customer-facing delivery signals indicate support service delivery.

  - id: maintenance_bugfix
    priority: 90
    when:
      any:
        - feature: git.issue_labels
          op: overlaps
          value: ["bug", "incident", "maintenance"]
        - feature: git.branch
          op: contains
          value: fix/
        - feature: git.deployment_target
          op: eq
          value: production
    decision:
      work_category: maintenance_bugfix
      policy_outcome: maintenance_non_capitalizable
      cost_category: software_maintenance
      confidence: 0.9
    explanation: Incident, bug, maintenance, or production hotfix context indicates maintenance rather than new software creation.

  - id: internal_use_software
    priority: 82
    when:
      any:
        - feature: git.repository
          op: contains
          value: internal
        - feature: labels
          op: overlaps
          value: ["internal-tool", "ops"]
    decision:
      work_category: internal_use_software
      policy_outcome: capitalize_candidate
      cost_category: internal_software
      confidence: 0.84
    explanation: Repository or labels indicate internal-use software work that may warrant further capitalization review.

  - id: external_product_development
    priority: 80
    when:
      any:
        - feature: git.repository
          op: contains
          value: product
        - feature: labels
          op: overlaps
          value: ["feature", "product"]
        - feature: objective
          op: contains
          value: external product
    decision:
      work_category: external_product_development
      policy_outcome: capitalize_candidate
      cost_category: product_development
      confidence: 0.86
    explanation: Product repository and feature signals indicate new product development work.

  - id: exploratory_r_and_d
    priority: 70
    when:
      any:
        - feature: labels
          op: overlaps
          value: ["experiment", "prototype", "research"]
        - feature: objective
          op: contains
          value: explore
    decision:
      work_category: research_and_development
      policy_outcome: review_required
      cost_category: research
      confidence: 0.72
      requires_review: true
    explanation: Experimental or exploratory context suggests research and development, but more evidence is needed.

  - id: high_cost_low_review
    priority: 60
    when:
      all:
        - feature: total_cost
          op: gte
          value: 0.05
        - feature: has_human_review
          op: eq
          value: false
    decision:
      work_category: general_admin
      policy_outcome: review_required
      cost_category: ambiguous_ai_work
      confidence: 0.55
      requires_review: true
    explanation: High-cost work without human review is ambiguous enough to require additional review.
""",
    "software_capex_review_v1.yaml": """policy_pack_id: software_capex_review_v1
version: 1.0.0
basis: software_capex_review_v1
title: Software Capex Review
description: Conservative capex-oriented policy pack for software work that distinguishes maintenance from capitalizable development candidates.
default_work_category: unknown
default_policy_outcome: review_required
rules:
  - id: maintenance_hotfix
    priority: 100
    when:
      any:
        - feature: git.issue_labels
          op: overlaps
          value: ["bug", "incident", "maintenance"]
        - feature: git.branch
          op: contains
          value: fix/
        - feature: git.deployment_target
          op: eq
          value: production
    decision:
      work_category: maintenance_bugfix
      policy_outcome: maintenance_non_capitalizable
      cost_category: software_maintenance
      confidence: 0.96
    explanation: Maintenance and production hotfix signals indicate non-capitalizable software maintenance.

  - id: internal_use_software
    priority: 90
    when:
      any:
        - feature: git.repository
          op: contains
          value: internal
        - feature: labels
          op: overlaps
          value: ["internal-tool", "ops"]
    decision:
      work_category: internal_use_software
      policy_outcome: capitalize_candidate
      cost_category: internal_software
      confidence: 0.84
      requires_review: true
    explanation: Internal-use software is a capitalization candidate but should remain review-required in V1.

  - id: product_feature
    priority: 80
    when:
      any:
        - feature: labels
          op: overlaps
          value: ["feature", "product"]
        - feature: objective
          op: contains
          value: external product
    decision:
      work_category: external_product_development
      policy_outcome: capitalize_candidate
      cost_category: product_development
      confidence: 0.91
    explanation: New product feature delivery is a software development activity that merits capitalization review.
""",
    "us_gaap_book_v1.yaml": """policy_pack_id: us_gaap_book_v1
version: 0.1.0
basis: us_gaap_book_v1
title: US GAAP Book Example
description: Conservative example policy pack that maps work units into US GAAP-oriented candidate treatments for review.
default_work_category: general_admin
default_policy_outcome: review_required
rules:
  - id: gaap_maintenance
    priority: 100
    when:
      any:
        - feature: git.issue_labels
          op: overlaps
          value: ["bug", "maintenance", "incident"]
    decision:
      work_category: maintenance_bugfix
      policy_outcome: maintenance_non_capitalizable
      confidence: 0.9
    explanation: Maintenance signals map to non-capitalizable maintenance candidate treatment.
  - id: gaap_internal_use
    priority: 90
    when:
      any:
        - feature: git.repository
          op: contains
          value: internal
    decision:
      work_category: internal_use_software
      policy_outcome: capitalize_candidate
      confidence: 0.78
      requires_review: true
    explanation: Internal-use software may be capitalizable under a separate stage and evidence review.
""",
    "ifrs_book_v1.yaml": """policy_pack_id: ifrs_book_v1
version: 0.1.0
basis: ifrs_book_v1
title: IFRS Book Example
description: Example IFRS-oriented candidate policy pack that separates research from development and preserves ambiguity.
default_work_category: general_admin
default_policy_outcome: review_required
rules:
  - id: ifrs_research
    priority: 100
    when:
      any:
        - feature: labels
          op: overlaps
          value: ["research", "prototype", "experiment"]
    decision:
      work_category: research_and_development
      policy_outcome: expense_now
      confidence: 0.84
      requires_review: true
    explanation: Research-phase indicators suggest immediate expensing under a conservative IFRS interpretation.
  - id: ifrs_development
    priority: 90
    when:
      any:
        - feature: labels
          op: overlaps
          value: ["feature", "product"]
        - feature: git.repository
          op: contains
          value: product
    decision:
      work_category: external_product_development
      policy_outcome: capitalize_candidate
      confidence: 0.75
      requires_review: true
    explanation: Development-phase product signals may support capitalization pending stricter evidence review.
""",
    "tax_r_and_d_v1.yaml": """policy_pack_id: tax_r_and_d_v1
version: 0.1.0
basis: tax_r_and_d_v1
title: Tax R&D Example
description: Example tax-oriented policy pack for surfacing work that could be relevant to R&D studies.
default_work_category: general_admin
default_policy_outcome: review_required
rules:
  - id: tax_rd_candidate
    priority: 100
    when:
      any:
        - feature: labels
          op: overlaps
          value: ["experiment", "prototype", "feature"]
        - feature: kind
          op: eq
          value: software_delivery
    decision:
      work_category: research_and_development
      policy_outcome: review_required
      confidence: 0.7
      requires_review: true
    explanation: Software development or experimental signals may be relevant to an R&D study but need tax review.
""",
}


def ensure_builtin_policies(destination: Path) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for filename, contents in BUILTIN_POLICY_PACKS.items():
        path = destination / filename
        if not path.exists() or path.read_text(encoding="utf-8") != contents:
            path.write_text(contents, encoding="utf-8")
        written.append(path)
    return written
