"""
LLM Exception Classes
====================

Simple exception hierarchy for LLM-related errors.
"""

from ..core.exceptions import SymbolicaError


class LLMError(SymbolicaError):
    """Base exception for LLM-related errors."""
    pass


class LLMTimeoutError(LLMError):
    """LLM call timed out."""
    pass


class LLMValidationError(LLMError):
    """LLM response validation failed."""
    pass 