"""
LLM Integration Module
======================

Simple integration for LLM clients in rule evaluation.
Provides PROMPT() function for hybrid symbolic-neural reasoning
and prompt() wrapper for graceful fallback evaluation.
"""

from .exceptions import LLMError, LLMTimeoutError, LLMValidationError
from .client_adapter import LLMClientAdapter
from .config import LLMConfig
from .fallback_evaluator import FallbackEvaluator, FallbackResult

__all__ = [
    'LLMError',
    'LLMTimeoutError', 
    'LLMValidationError',
    'LLMClientAdapter',
    'LLMConfig',
    'FallbackEvaluator',
    'FallbackResult'
] 