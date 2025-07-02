from __future__ import annotations

import pathlib
from typing import Any, Dict, List, TypedDict, Union

import yaml


class RawRule(TypedDict):
    id: str
    priority: int
    agent: str
    if_: Any
    then: Dict[str, Any]
    tags: List[str]


def _load_yaml(source: str | pathlib.Path) -> dict:
    if isinstance(source, (pathlib.Path, str)) and pathlib.Path(source).exists():
        text = pathlib.Path(source).read_text(encoding="utf-8")
    else:
        text = str(source)
    try:
        return yaml.safe_load(text) or {}
    except Exception as exc:
        raise ValueError(f"YAML parse error: {exc}") from exc


def _require_keys(mapping: dict, keys: list[str], ctx: str) -> None:
    for k in keys:
        if k not in mapping:
            raise ValueError(f"{ctx} missing mandatory key '{k}'")


def _parse_rule(rule_data: dict, source_context: str = "") -> RawRule:
    """Parse a single rule dictionary into RawRule format."""
    _require_keys(rule_data, ["id"], f"rule {source_context}")
    
    # Handle conditions (required)
    conditions = rule_data.get("conditions", [])
    if not conditions:
        raise ValueError(f"Rule {rule_data['id']} missing 'conditions'")
    
    # Convert conditions list to if_ expression
    if isinstance(conditions, list):
        if_expr = " and ".join(f"({cond})" for cond in conditions)
    else:
        if_expr = str(conditions)
    
    # Handle actions (required)
    actions = rule_data.get("actions", [])
    if not actions:
        raise ValueError(f"Rule {rule_data['id']} missing 'actions'")
    
    # Convert actions to then format
    then_block = {"set": {}}
    for action in actions:
        if isinstance(action, dict):
            then_block["set"].update(action)
        elif isinstance(action, str) and ":" in action:
            key, value = action.split(":", 1)
            then_block["set"][key.strip()] = value.strip()

    return RawRule(
        id=str(rule_data["id"]),
        priority=int(rule_data.get("priority", 50)),
        agent=str(rule_data.get("agent", "Default")),
        if_=if_expr,
        then=then_block,
        tags=list(rule_data.get("tags", [])),
    )


def parse_yaml_file(source: str | pathlib.Path) -> List[RawRule]:
    """Parse YAML file containing rules array."""
    doc = _load_yaml(source)
    source_name = str(source) if isinstance(source, pathlib.Path) else "input"
    
    # Only support standardized rules: array format
    if "rules" not in doc or not isinstance(doc["rules"], list):
        raise ValueError(f"YAML must contain 'rules:' array. File: {source_name}")
    
    parsed_rules = []
    for i, rule_data in enumerate(doc["rules"]):
        context = f"{source_name}[{i}]"
        parsed_rules.append(_parse_rule(rule_data, context))
    
    return parsed_rules


# Legacy function for backward compatibility
def parse_yaml(source: str | pathlib.Path) -> List[RawRule]:
    """Parse YAML file - now always returns list."""
    return parse_yaml_file(source)
