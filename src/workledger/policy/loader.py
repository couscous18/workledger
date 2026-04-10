from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from workledger.models import PolicyPack


def load_policy_pack(path: Path) -> PolicyPack:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return PolicyPack.model_validate(payload)


def resolve_policy_pack_path(policies_dir: Path, policy_name: str) -> Path:
    candidate_name = policy_name.strip()
    if not candidate_name:
        raise ValueError("policy name must not be empty")
    if "/" in candidate_name or "\\" in candidate_name:
        raise ValueError("policy must be an installed policy filename, not a filesystem path")
    if not candidate_name.endswith(".yaml"):
        candidate_name = f"{candidate_name}.yaml"
    candidate_path = (policies_dir / candidate_name).resolve()
    if candidate_path.parent != policies_dir.resolve():
        raise ValueError("policy must resolve inside the installed policies directory")
    if not candidate_path.exists():
        raise FileNotFoundError(f"unknown installed policy pack: {candidate_name}")
    return candidate_path


def list_policy_packs(policies_dir: Path) -> list[PolicyPack]:
    return [load_policy_pack(path) for path in sorted(policies_dir.glob("*.yaml"))]


def validate_policy_pack(path: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        pack = load_policy_pack(path)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        return False, [str(exc)]
    if not pack.rules:
        errors.append("policy pack must contain at least one rule")
    seen_ids: set[str] = set()
    for rule in pack.rules:
        rule_id = rule.get("id")
        if not rule_id:
            errors.append("rule missing id")
        elif rule_id in seen_ids:
            errors.append(f"duplicate rule id: {rule_id}")
        else:
            seen_ids.add(rule_id)
        if "when" not in rule:
            errors.append(f"rule {rule_id} missing when block")
        if "decision" not in rule:
            errors.append(f"rule {rule_id} missing decision block")
    return not errors, errors
