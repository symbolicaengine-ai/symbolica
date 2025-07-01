from __future__ import annotations

import pathlib
from typing import Any, Dict, List, TypedDict

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


def parse_yaml(source: str | pathlib.Path) -> RawRule:
    doc = _load_yaml(source)
    if "rule" not in doc or not isinstance(doc["rule"], dict):
        raise ValueError("Top-level mapping 'rule:' is required")

    rule_block = doc["rule"]
    _require_keys(rule_block, ["id", "if", "then"], "rule")

    then_block = rule_block["then"]
    if "set" not in then_block:
        raise ValueError("then.set block is mandatory for every rule")

    return RawRule(
        id=str(rule_block["id"]),
        priority=int(rule_block.get("priority", 50)),
        agent=str(rule_block.get("agent", "Default")),
        if_=rule_block["if"],
        then=then_block,
        tags=list(rule_block.get("tags", [])),
    )
