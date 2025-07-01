"""
symbolica.compiler.lint
=======================

Static checks for YAML rule files.  Fail-fast on:

* Tabs used for indentation
* Duplicate rule IDs
* Missing mandatory keys (id, conditions, actions)
* YAML syntax errors

Warnings (non-fatal unless --strict):

* Inline condition > 120 characters
* Mixed AND/OR in a single string without parentheses

Used by the CLI command::

    symbolica lint   --rules-dir  symbolica_rules

Returns number of *errors* (exit non-zero on CI).
"""
from __future__ import annotations

import pathlib
import re
import sys
from typing import Dict, List

import yaml

MANDATORY_KEYS = ("id",)  # conditions and actions are validated separately
INDENT_RE = re.compile(r"^\t+", flags=re.M)  # any tab at line start
LONG_EXPR_RE = re.compile(r"\b(and|or)\b.*\b(and|or)\b", re.I)


class LintResult:
    __slots__ = ("errors", "warnings")

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def err(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)


# ---------------------------------------------------------------- utilities
def _load_yaml(file: pathlib.Path, res: LintResult):
    txt = file.read_text(encoding="utf-8")

    if INDENT_RE.search(txt):
        res.err(f"{file}: TAB character found in indentation")
        # Continue to parse, tabs break YAML anyway.

    try:
        return yaml.safe_load(txt)
    except Exception as exc:  # pylint: disable=broad-except
        res.err(f"{file}: YAML parse error → {exc}")
        return None


def _lint_rule(rule_data: dict, file: pathlib.Path, res: LintResult, rule_index: int = 0):
    """Lint standardized rule format: { id, conditions, actions }"""
    rule_id = rule_data.get('id', f'rule_{rule_index}')
    
    # Check mandatory keys
    for key in MANDATORY_KEYS:
        if key not in rule_data:
            res.err(f"{file}: rule '{rule_id}' missing '{key}'")
            return
    
    # Check conditions
    conditions = rule_data.get("conditions", [])
    if not conditions:
        res.err(f"{file}: rule '{rule_id}' missing 'conditions' array")
    elif isinstance(conditions, list):
        for i, cond in enumerate(conditions):
            if isinstance(cond, str) and len(cond) > 120:
                res.warn(f"{file}: rule '{rule_id}' condition {i} >120 chars")
            if isinstance(cond, str) and LONG_EXPR_RE.search(cond) and "(" not in cond:
                res.warn(f"{file}: rule '{rule_id}' condition {i} mixed 'and/or' without parentheses")
    
    # Check actions
    actions = rule_data.get("actions", [])
    if not actions:
        res.err(f"{file}: rule '{rule_id}' missing 'actions' array")


def _lint_document(doc: dict, file: pathlib.Path, res: LintResult) -> List[str]:
    """Lint a parsed YAML document and return list of rule IDs found."""
    rule_ids = []
    
    # Only support standardized rules: array format
    if "rules" not in doc or not isinstance(doc["rules"], list):
        res.err(f"{file}: must contain 'rules:' array")
        return rule_ids
    
    for i, rule_data in enumerate(doc["rules"]):
        _lint_rule(rule_data, file, res, i)
        rule_id = rule_data.get("id")
        if rule_id:
            rule_ids.append(rule_id)
    
    return rule_ids


# ---------------------------------------------------------------- main entry
def lint_folder(rules_dir: str | pathlib.Path, strict: bool = False) -> int:
    """
    Lint every *.yaml under *rules_dir*.  Returns error count.
    If *strict* is True, warnings are counted as errors.
    """
    res = LintResult()
    rule_ids: set[str] = set()

    path = pathlib.Path(rules_dir)
    for file in path.rglob("*.yaml"):
        data = _load_yaml(file, res)
        if not data:
            continue

        # Lint the document and collect rule IDs
        file_rule_ids = _lint_document(data, file, res)
        
        # Check for duplicate IDs across all files
        for rule_id in file_rule_ids:
            if rule_id in rule_ids:
                res.err(f"{file}: duplicate id '{rule_id}'")
            rule_ids.add(rule_id)

    # report
    for w in res.warnings:
        print("⚠", w, file=sys.stderr)
    for e in res.errors:
        print("❌", e, file=sys.stderr)

    err_count = len(res.errors) + (len(res.warnings) if strict else 0)
    if err_count:
        print(f"\n{err_count} problem(s) found.", file=sys.stderr)
    else:
        print("No lint errors.", file=sys.stderr)
    return err_count
