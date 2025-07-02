"""
symbolica.compiler.schema
=========================

Simple rule schema validation for contract enforcement.

Validates the canonical rule structure:
- Required: id (string), conditions (array), actions (array)
- Optional: priority (int), tags (array), description (string)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set


class ValidationResult:
    """Simple validation result."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    @property
    def valid(self) -> bool:
        return len(self.errors) == 0
    
    def add_error(self, message: str) -> None:
        self.errors.append(message)
    
    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


def validate_rule_document(doc: Dict[str, Any], file_path: str = "document") -> ValidationResult:
    """
    Validate a rule document against the basic schema.
    
    Args:
        doc: Parsed YAML document
        file_path: Source file path for error reporting
        
    Returns:
        ValidationResult with validation outcome
    """
    result = ValidationResult()
    
    # Check document structure
    if not isinstance(doc, dict):
        result.add_error(f"{file_path}: Document must be a dictionary")
        return result
    
    if "rules" not in doc:
        result.add_error(f"{file_path}: Document must contain 'rules' array")
        return result
    
    if not isinstance(doc["rules"], list):
        result.add_error(f"{file_path}: 'rules' must be an array")
        return result
    
    if not doc["rules"]:
        result.add_warning(f"{file_path}: Document contains no rules")
        return result
    
    # Validate each rule
    rule_ids: Set[str] = set()
    
    for i, rule in enumerate(doc["rules"]):
        rule_path = f"{file_path}[{i}]"
        
        # Basic rule structure
        if not isinstance(rule, dict):
            result.add_error(f"{rule_path}: Rule must be a dictionary")
            continue
        
        rule_id = rule.get("id", f"rule_{i}")
        
        # Required fields
        if "id" not in rule:
            result.add_error(f"{rule_path}: Missing required field 'id'")
        elif not isinstance(rule["id"], str) or not rule["id"].strip():
            result.add_error(f"{rule_path}: Field 'id' must be non-empty string")
        
        if "conditions" not in rule:
            result.add_error(f"{rule_path}: Missing required field 'conditions'")
        elif not isinstance(rule["conditions"], list) or not rule["conditions"]:
            result.add_error(f"{rule_path}: Field 'conditions' must be non-empty array")
        
        if "actions" not in rule:
            result.add_error(f"{rule_path}: Missing required field 'actions'")
        elif not isinstance(rule["actions"], list) or not rule["actions"]:
            result.add_error(f"{rule_path}: Field 'actions' must be non-empty array")
        
        # Optional field types
        if "priority" in rule and not isinstance(rule["priority"], int):
            result.add_error(f"{rule_path}: Field 'priority' must be integer")
        
        if "tags" in rule and not isinstance(rule["tags"], list):
            result.add_error(f"{rule_path}: Field 'tags' must be array")
        
        if "description" in rule and not isinstance(rule["description"], str):
            result.add_error(f"{rule_path}: Field 'description' must be string")
        
        # Check for duplicate IDs
        if "id" in rule and isinstance(rule["id"], str):
            if rule["id"] in rule_ids:
                result.add_error(f"{rule_path}: Duplicate rule ID '{rule['id']}'")
            rule_ids.add(rule["id"])
    
    return result
    
def get_schema_info() -> Dict[str, Any]:
    """Get basic information about the rule schema."""
    return {
        "version": "1.0",
        "required_fields": ["id", "conditions", "actions"],
        "optional_fields": ["priority", "tags", "description"],
        "validation": "basic_contract_enforcement"
    } 