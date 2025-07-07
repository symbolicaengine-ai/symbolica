"""
Symbolica Core
==============

Core domain models, interfaces, and exceptions.
This is the foundation layer - no external dependencies.
"""

# Domain models
from .models import (
    RuleId, Priority, Condition, Action, Rule, Facts, 
    ExecutionResult, ExecutionContext, RuleSet, TraceLevel,
    # Factory functions
    rule_id, priority, condition, action_set, action_call, facts
)

# Interfaces (only where needed for extensibility)
from .interfaces import (
    ConditionEvaluator, ActionExecutor, ExecutionStrategy,
    Cache, Tracer, RuleLoader, FunctionRegistry
)

# Exceptions
from .exceptions import (
    SymbolicaError, ValidationError, CompilationError, 
    ExecutionError, EvaluationError, ActionExecutionError,
    LoadError, CacheError, ConfigurationError
)

__all__ = [
    # Domain models
    "RuleId", "Priority", "Condition", "Action", "Rule", "Facts",
    "ExecutionResult", "ExecutionContext", "RuleSet", "TraceLevel",
    
    # Factory functions
    "rule_id", "priority", "condition", "action_set", "action_call", "facts",
    
    # Interfaces
    "ConditionEvaluator", "ActionExecutor", "ExecutionStrategy",
    "Cache", "Tracer", "RuleLoader", "FunctionRegistry",
    
    # Exceptions
    "SymbolicaError", "ValidationError", "CompilationError",
    "ExecutionError", "EvaluationError", "ActionExecutionError", 
    "LoadError", "CacheError", "ConfigurationError",
] 