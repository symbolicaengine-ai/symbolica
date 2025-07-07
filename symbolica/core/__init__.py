"""
Symbolica Core Module
====================

Essential data models and interfaces for AI agent reasoning.
"""

# Core models
from .models import Rule, Facts, ExecutionResult, ExecutionContext, TraceLevel, facts

# Essential interfaces  
from .interfaces import ConditionEvaluator, ActionExecutor

# Exceptions
from .exceptions import SymbolicaError, ValidationError, ExecutionError, EvaluationError

__all__ = [
    # Core models
    "Rule",
    "Facts", 
    "ExecutionResult",
    "ExecutionContext",
    "TraceLevel",
    "facts",
    
    # Interfaces
    "ConditionEvaluator",
    "ActionExecutor",
    
    # Exceptions
    "SymbolicaError",
    "ValidationError",
    "ExecutionError", 
    "EvaluationError"
] 