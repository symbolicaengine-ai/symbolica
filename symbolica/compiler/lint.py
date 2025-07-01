"""
symbolica.compiler.lint
=======================

Static checks for YAML rule files with comprehensive schema validation.

Validates:
* Rule structure against canonical schema
* Required and optional fields
* Field types and constraints
* ID format and uniqueness
* Expression syntax
* YAML formatting (tabs, syntax errors)

Used by the CLI command::

    symbolica lint --rules-dir symbolica_rules [--strict]

Returns number of *errors* (exit non-zero on CI).
"""
from __future__ import annotations

import pathlib
import re
import sys
from typing import Dict, List

import yaml

from .schema import validate_rule_document

# Legacy patterns for additional checks
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


def _lint_document(doc: dict, file: pathlib.Path, res: LintResult, strict: bool = False) -> List[str]:
    """
    Lint a parsed YAML document using comprehensive schema validation.
    
    Args:
        doc: Parsed YAML document
        file: Source file path
        res: LintResult to accumulate issues
        strict: If True, warnings are treated as errors
        
    Returns:
        List of rule IDs found in the document
    """
    # Use schema validation for contract enforcement
    validation_result = validate_rule_document(doc, str(file))
    
    # Add schema issues to lint result
    for error in validation_result.errors:
        res.err(error)
    for warning in validation_result.warnings:
        res.warn(warning)
    
    # Extract rule IDs for duplicate checking across files
    rule_ids = []
    if isinstance(doc, dict) and "rules" in doc and isinstance(doc["rules"], list):
        for rule in doc["rules"]:
            if isinstance(rule, dict) and "id" in rule:
                rule_ids.append(rule["id"])
    
    # Additional legacy checks for expression patterns
    _lint_legacy_patterns(doc, file, res)
    
    return rule_ids


def _lint_legacy_patterns(doc: dict, file: pathlib.Path, res: LintResult):
    """Additional legacy pattern checks for backwards compatibility."""
    if not isinstance(doc, dict) or "rules" not in doc:
        return
    
    for i, rule in enumerate(doc.get("rules", [])):
        if not isinstance(rule, dict):
            continue
            
        rule_id = rule.get("id", f"rule_{i}")
        conditions = rule.get("conditions", [])
        
        if isinstance(conditions, list):
            for j, cond in enumerate(conditions):
                if isinstance(cond, str):
                    # Check for mixed AND/OR without parentheses
                    if LONG_EXPR_RE.search(cond) and "(" not in cond:
                        res.warn(f"{file}: rule '{rule_id}' condition {j} has mixed 'and/or' without parentheses")


# ---------------------------------------------------------------- main entry
def lint_folder(rules_dir: str | pathlib.Path, strict: bool = False) -> int:
    """
    Lint every *.yaml under *rules_dir* with comprehensive schema validation.
    
    Args:
        rules_dir: Directory containing rule files
        strict: If True, warnings are counted as errors
        
    Returns:
        Number of errors found (for CI exit codes)
    """
    res = LintResult()
    rule_ids: set[str] = set()

    path = pathlib.Path(rules_dir)
    file_count = 0
    
    for file in path.rglob("*.yaml"):
        file_count += 1
        data = _load_yaml(file, res)
        if not data:
            continue

        # Comprehensive schema validation
        file_rule_ids = _lint_document(data, file, res, strict)
        
        # Check for duplicate IDs across all files
        for rule_id in file_rule_ids:
            if rule_id in rule_ids:
                res.err(f"{file}: duplicate rule ID '{rule_id}' (already defined in another file)")
            rule_ids.add(rule_id)

    # Enhanced reporting
    if res.warnings:
        print(f"\nWARNINGS ({len(res.warnings)}):", file=sys.stderr)
        for w in res.warnings:
            print(f"{w}", file=sys.stderr)
    
    if res.errors:
        print(f"\nERRORS ({len(res.errors)}):", file=sys.stderr)
        for e in res.errors:
            print(f"{e}", file=sys.stderr)

    # Summary
    err_count = len(res.errors) + (len(res.warnings) if strict else 0)
    total_rules = len(rule_ids)
    
    if err_count:
        print(f"\nSUMMARY: {err_count} problem(s) found in {file_count} files ({total_rules} rules)", file=sys.stderr)
        if strict and res.warnings:
            print("   (warnings treated as errors in strict mode)", file=sys.stderr)
    else:
        print(f"SUCCESS: {file_count} files validated, {total_rules} rules passed schema validation", file=sys.stderr)
    
    return err_count
