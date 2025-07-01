"""
symbolica.exceptions
===================

Exception classes for Symbolica.
"""


class SymbolicaError(Exception):
    """Base exception for Symbolica errors."""
    pass


class RuleEngineError(SymbolicaError):
    """Rule engine configuration or execution error."""
    pass


class RegistryNotFoundError(SymbolicaError):
    """Registry file not found."""
    pass 