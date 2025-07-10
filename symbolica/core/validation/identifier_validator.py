"""
Identifier Validator
====================

Focused validator for identifiers and reserved keyword checking.
Extracted from SchemaValidator to follow Single Responsibility Principle.
"""

from typing import Set
from ..exceptions import ValidationError
from .schema_constants import SchemaConstants


class IdentifierValidator:
    """Validates identifiers against reserved keywords and Python naming rules."""
    
    def __init__(self):
        """Initialize identifier validator with schema constants."""
        self._constants = SchemaConstants()
    
    def validate_identifier(self, identifier: str, context: str) -> None:
        """Validate that an identifier is not a reserved keyword.
        
        Args:
            identifier: The identifier to validate
            context: Context description for error messages
            
        Raises:
            ValidationError: If identifier is reserved
        """
        if not isinstance(identifier, str):
            raise ValidationError(f"{context}: identifier must be a string")
        
        if not identifier.strip():
            raise ValidationError(f"{context}: identifier cannot be empty or whitespace")
        
        if identifier in self._constants.SYSTEM_RESERVED_KEYWORDS:
            raise ValidationError(
                f"{context}: '{identifier}' is a reserved keyword and cannot be used. "
                f"Reserved keywords include system fields, Python built-ins, and function names."
            )
        
        # Additional validation for Python identifier rules
        if not identifier.isidentifier():
            raise ValidationError(
                f"{context}: '{identifier}' is not a valid identifier. "
                f"Identifiers must start with a letter or underscore, "
                f"followed by letters, digits, or underscores."
            )
    
    def get_reserved_keywords(self) -> Set[str]:
        """Get the complete set of reserved keywords.
        
        Returns:
            Set of all reserved keywords
        """
        return self._constants.SYSTEM_RESERVED_KEYWORDS.copy()
    
    def is_reserved(self, identifier: str) -> bool:
        """Check if an identifier is reserved.
        
        Args:
            identifier: The identifier to check
            
        Returns:
            True if the identifier is reserved
        """
        return identifier in self._constants.SYSTEM_RESERVED_KEYWORDS 