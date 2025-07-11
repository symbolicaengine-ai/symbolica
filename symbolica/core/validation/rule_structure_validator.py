"""
Rule Structure Validator
========================

Focused validator for individual rule structure.
Extracted from SchemaValidator to follow Single Responsibility Principle.
"""

from typing import Dict, Any
from ..exceptions import ValidationError
from .schema_constants import SchemaConstants
from .identifier_validator import IdentifierValidator


class RuleStructureValidator:
    """Validates individual rule structure against schema requirements."""
    
    def __init__(self):
        """Initialize rule structure validator with dependencies."""
        self._constants = SchemaConstants()
        self._identifier_validator = IdentifierValidator()
    
    def validate_rule_structure(self, rule_dict: Dict[str, Any], rule_index: int) -> None:
        """Validate individual rule structure.
        
        Args:
            rule_dict: Rule dictionary
            rule_index: Index of rule in list (for error messages)
            
        Raises:
            ValidationError: If rule structure is invalid
        """
        if not isinstance(rule_dict, dict):
            raise ValidationError(
                f"Rule at index {rule_index} must be a dictionary. "
                f"Got {type(rule_dict).__name__}."
            )
        
        # Check for required fields
        missing_fields = self._constants.REQUIRED_RULE_FIELDS - set(rule_dict.keys())
        if missing_fields:
            # Handle alternative field names
            alternatives = {
                'condition': rule_dict.get('if'),
                'actions': rule_dict.get('then')
            }
            
            actual_missing = []
            for field in missing_fields:
                if field not in alternatives or alternatives[field] is None:
                    actual_missing.append(field)
            
            if actual_missing:
                raise ValidationError(
                    f"Rule at index {rule_index} missing required fields: {sorted(actual_missing)}. "
                    f"Required fields are: {sorted(self._constants.REQUIRED_RULE_FIELDS)}. "
                    f"Alternative field names: 'if' for 'condition', 'then' for 'actions'."
                )
        
        # Check for unknown fields
        unknown_fields = set(rule_dict.keys()) - self._constants.ALLOWED_RULE_FIELDS
        if unknown_fields:
            raise ValidationError(
                f"Rule at index {rule_index} has unknown fields: {sorted(unknown_fields)}. "
                f"Allowed fields are: {sorted(self._constants.ALLOWED_RULE_FIELDS)}"
            )
        
        # Validate field types
        for field, value in rule_dict.items():
            if field in self._constants.FIELD_TYPE_VALIDATORS:
                if not self._constants.FIELD_TYPE_VALIDATORS[field](value):
                    expected_type = self._constants.get_expected_type_description(field)
                    raise ValidationError(
                        f"Rule at index {rule_index}, field '{field}' has invalid type. "
                        f"Expected {expected_type}, got {type(value).__name__}."
                    )
        
        # Validate rule ID is not reserved
        if 'id' in rule_dict:
            self._identifier_validator.validate_identifier(
                rule_dict['id'], 
                f"Rule ID at index {rule_index}"
            )
        
        # Validate structured conditions
        condition = rule_dict.get('condition') or rule_dict.get('if')
        if isinstance(condition, dict):
            self._validate_structured_condition(condition, rule_index)
        
        # Validate fact and action names
        if 'facts' in rule_dict:
            self._validate_fact_action_names(
                rule_dict['facts'], 
                f"Rule at index {rule_index}, facts"
            )
        
        actions = rule_dict.get('actions') or rule_dict.get('then', {})
        self._validate_fact_action_names(
            actions, 
            f"Rule at index {rule_index}, actions"
        )
    
    def _validate_structured_condition(self, condition_dict: Dict[str, Any], rule_index: int) -> None:
        """Validate structured condition keywords."""
        for key in condition_dict.keys():
            if key not in self._constants.CONDITION_KEYWORDS:
                raise ValidationError(
                    f"Rule at index {rule_index}: unknown condition keyword '{key}'. "
                    f"Valid condition keywords are: {sorted(self._constants.CONDITION_KEYWORDS)}"
                )
    
    def _validate_fact_action_names(self, items: Dict[str, Any], context: str) -> None:
        """Validate fact and action names are not reserved."""
        for name in items.keys():
            self._identifier_validator.validate_identifier(name, f"{context}, field '{name}'") 