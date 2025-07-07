"""
Symbolica Core Package
=====================

Core domain models and engine for deterministic AI agent reasoning.
"""

from .models import (
    Rule, Facts, ExecutionContext, ExecutionResult, 
    RuleEvaluationTrace, ConditionTrace, FieldAccess, TraceLevel,
    facts
)
from .engine import Engine
from .exceptions import SymbolicaError, ValidationError, EvaluationError
from .interfaces import ConditionEvaluator, ActionExecutor, ExecutionStrategy

__all__ = [
    # Core models
    'Rule', 'Facts', 'ExecutionContext', 'ExecutionResult',
    
    # Enhanced tracing
    'RuleEvaluationTrace', 'ConditionTrace', 'FieldAccess', 'TraceLevel',
    
    # Engine
    'Engine',
    
    # Exceptions
    'SymbolicaError', 'ValidationError', 'EvaluationError',
    
    # Interfaces
    'ConditionEvaluator', 'ActionExecutor', 'ExecutionStrategy',
    
    # Factories
    'facts'
] 