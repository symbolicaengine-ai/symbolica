"""
Schema Validator Facade
=======================

Refactored facade that delegates to focused validator components.
Follows Single Responsibility Principle by composing specialized validators.
"""

from typing import Dict, Any, Set
from ..exceptions import ValidationError
from .yaml_structure_validator import YamlStructureValidator
from .rule_structure_validator import RuleStructureValidator
from .identifier_validator import IdentifierValidator
from .schema_documentation_generator import SchemaDocumentationGenerator


class SchemaValidator:
    """Facade that orchestrates focused schema validation components."""
    
    def __init__(self):
        """Initialize schema validator with focused components."""
        self._yaml_validator = YamlStructureValidator()
        self._rule_validator = RuleStructureValidator()
        self._identifier_validator = IdentifierValidator()
        self._doc_generator = SchemaDocumentationGenerator()
    
    def validate_yaml_structure(self, data: Any) -> None:
        """Validate the overall YAML structure.
        
        Args:
            data: Parsed YAML data
            
        Raises:
            ValidationError: If structure is invalid
        """
        self._yaml_validator.validate_yaml_structure(data)
    
    def validate_rule_structure(self, rule_dict: Dict[str, Any], rule_index: int) -> None:
        """Validate individual rule structure.
        
        Args:
            rule_dict: Rule dictionary
            rule_index: Index of rule in list (for error messages)
            
        Raises:
            ValidationError: If rule structure is invalid
        """
        self._rule_validator.validate_rule_structure(rule_dict, rule_index)
    
    def validate_identifier(self, identifier: str, context: str) -> None:
        """Validate that an identifier is not a reserved keyword.
        
        Args:
            identifier: The identifier to validate
            context: Context description for error messages
            
        Raises:
            ValidationError: If identifier is reserved
        """
        self._identifier_validator.validate_identifier(identifier, context)
    
    def get_reserved_keywords(self) -> Set[str]:
        """Get the complete set of reserved keywords.
        
        Returns:
            Set of all reserved keywords
        """
        return self._identifier_validator.get_reserved_keywords()
    
    def generate_schema_documentation(self) -> str:
        """Generate human-readable schema documentation.
        
        Returns:
            Formatted schema documentation
        """
        return self._doc_generator.generate_schema_documentation() 