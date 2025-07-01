"""
symbolica.compiler.lint
=======================

Static checks for YAML rule files.  Fail-fast on:

* Tabs used for indentation
* Duplicate rule IDs
* Missing mandatory keys  (id / if / then.set)
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
from typing import Dict, List, Tuple

import yaml

MANDATORY_KEYS = ("id", "if", "then")
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


def _lint_rule(rule: Dict[str, any], file: pathlib.Path, res: LintResult):
    # mandatory keys
    if "rule" not in rule:
        res.err(f"{file}: top-level key 'rule' missing")
        return

    block = rule["rule"]
    for key in MANDATORY_KEYS:
        if key not in block:
            res.err(f"{file}: rule '{block.get('id','?')}' missing '{key}'")
            return

    # then.set presence
    if "set" not in block["then"]:
        res.err(f"{file}: rule '{block['id']}' missing 'then.set' dict")

    # expression lint
    cond = block["if"]
    if isinstance(cond, str):
        if len(cond) > 120:
            res.warn(f"{file}: rule '{block['id']}' condition >120 chars")
        if LONG_EXPR_RE.search(cond) and "(" not in cond:
            res.warn(
                f"{file}: rule '{block['id']}' mixed 'and/or' without parentheses"
            )


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

        # a file may contain one rule or a list
        rules = data if isinstance(data, list) else [data]
        for rule in rules:
            _lint_rule(rule, file, res)
            rid = rule.get("rule", {}).get("id")
            if rid:
                if rid in rule_ids:
                    res.err(f"{file}: duplicate id '{rid}'")
                rule_ids.add(rid)

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
