"""
Symbolica Core Package
=====================

Core domain models and engine for deterministic AI agent reasoning.
"""

from .models import Rule, Facts, ExecutionContext, ExecutionResult, facts
from .engine import Engine
from .exceptions import SymbolicaError, ValidationError, EvaluationError
from .interfaces import ConditionEvaluator, ExecutionStrategy

__all__ = [
    # Core models
    'Rule', 'Facts', 'ExecutionContext', 'ExecutionResult',
    
    # Engine
    'Engine',
    
    # Exceptions
    'SymbolicaError', 'ValidationError', 'EvaluationError',
    
    # Interfaces
    'ConditionEvaluator', 'ExecutionStrategy',
    
    # Factories
    'facts'
] 