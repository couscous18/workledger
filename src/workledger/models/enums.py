from __future__ import annotations

from enum import StrEnum


class SourceKind(StrEnum):
    OPENTELEMETRY = "opentelemetry"
    OPENINFERENCE = "openinference"
    JSONL = "jsonl"
    CLOUDEVENT = "cloudevent"
    SDK = "sdk"
    HUGGINGFACE = "huggingface"
    MANUAL = "manual"


class SpanKind(StrEnum):
    ROOT = "root"
    LLM = "llm"
    AGENT = "agent"
    TOOL = "tool"
    RETRIEVER = "retriever"
    EVALUATOR = "evaluator"
    GUARDRAIL = "guardrail"
    REVIEW = "review"
    IO = "io"
    OTHER = "other"


class ActorKind(StrEnum):
    HUMAN = "human"
    AGENT = "agent"
    HYBRID = "hybrid"
    SERVICE = "service"


class WorkCategory(StrEnum):
    RESEARCH_AND_DEVELOPMENT = "research_and_development"
    INTERNAL_USE_SOFTWARE = "internal_use_software"
    EXTERNAL_PRODUCT_DEVELOPMENT = "external_product_development"
    MAINTENANCE_BUGFIX = "maintenance_bugfix"
    SUPPORT_SERVICE_DELIVERY = "support_service_delivery"
    ADVERTISING_MARKETING = "advertising_marketing"
    SALES_ENABLEMENT = "sales_enablement"
    GENERAL_ADMIN = "general_admin"
    COMPLIANCE_LEGAL = "compliance_legal"
    DATA_OPS = "data_ops"
    UNKNOWN = "unknown"


class PolicyOutcome(StrEnum):
    EXPENSE_NOW = "expense_now"
    CAPITALIZE_CANDIDATE = "capitalize_candidate"
    MAINTENANCE_NON_CAPITALIZABLE = "maintenance_non_capitalizable"
    REVIEW_REQUIRED = "review_required"
    POLICY_EXCLUDED = "policy_excluded"


class TrustState(StrEnum):
    UNREVIEWED = "unreviewed"
    SELF_CHECKED = "self_checked"
    HUMAN_REVIEWED = "human_reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ReviewState(StrEnum):
    UNREVIEWED = "unreviewed"
    QUEUED = "queued"
    REVIEWED = "reviewed"
    OVERRIDDEN = "overridden"


class ImportanceBand(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceStrength(StrEnum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERIFIED = "verified"
