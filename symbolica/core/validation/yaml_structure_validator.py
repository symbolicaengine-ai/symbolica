"""
YAML Structure Validator
========================

Focused validator for top-level YAML structure.
Extracted from SchemaValidator to follow Single Responsibility Principle.
"""

from typing import Any
from ..exceptions import ValidationError
from .schema_constants import SchemaConstants


class YamlStructureValidator:
    """Validates top-level YAML structure against schema requirements."""
    
    def __init__(self):
        """Initialize YAML structure validator with schema constants."""
        self._constants = SchemaConstants()
    
    def validate_yaml_structure(self, data: Any) -> None:
        """Validate the overall YAML structure.
        
        Args:
            data: Parsed YAML data
            
        Raises:
            ValidationError: If structure is invalid
        """
        # Must be a dictionary
        if not isinstance(data, dict):
            raise ValidationError(
                "YAML root must be a dictionary. "
                f"Got {type(data).__name__}."
            )
        
        # Check for required top-level keys
        missing_keys = self._constants.REQUIRED_TOP_LEVEL_KEYS - set(data.keys())
        if missing_keys:
            raise ValidationError(
                f"Missing required top-level keys: {sorted(missing_keys)}. "
                f"Required keys are: {sorted(self._constants.REQUIRED_TOP_LEVEL_KEYS)}"
            )
        
        # Check for unknown top-level keys
        unknown_keys = set(data.keys()) - self._constants.ALLOWED_TOP_LEVEL_KEYS
        if unknown_keys:
            raise ValidationError(
                f"Unknown top-level keys: {sorted(unknown_keys)}. "
                f"Allowed keys are: {sorted(self._constants.ALLOWED_TOP_LEVEL_KEYS)}"
            )
        
        # Validate top-level field types
        for key, value in data.items():
            if key in self._constants.FIELD_TYPE_VALIDATORS:
                if not self._constants.FIELD_TYPE_VALIDATORS[key](value):
                    expected_type = self._constants.get_expected_type_description(key)
                    raise ValidationError(
                        f"Top-level field '{key}' has invalid type. "
                        f"Expected {expected_type}, got {type(value).__name__}."
                    )
        
        # Special validation for rules list
        if 'rules' in data:
            self._validate_rules_list(data['rules'])
    
    def _validate_rules_list(self, rules: Any) -> None:
        """Validate the rules list structure."""
        if not isinstance(rules, list):
            raise ValidationError(
                f"'rules' must be a list. Got {type(rules).__name__}."
            )
        
        if not rules:
            raise ValidationError("'rules' list cannot be empty.")
        
        # Validate each rule has basic structure
        for i, rule in enumerate(rules):
            if not isinstance(rule, dict):
                raise ValidationError(
                    f"Rule at index {i} must be a dictionary. "
                    f"Got {type(rule).__name__}."
                ) 