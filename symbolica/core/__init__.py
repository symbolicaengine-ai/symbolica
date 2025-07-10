"""
Symbolica Core Package
=====================

Core domain models and engine for deterministic AI agent reasoning.
"""

from .models import Rule, Facts, ExecutionContext, ExecutionResult, Goal, facts, goal
from .engine import Engine
from .exceptions import SymbolicaError, ValidationError, EvaluationError
from .interfaces import ConditionEvaluator, ExecutionStrategy
from .loader import RuleLoader, ConditionParser
from .function_registry import FunctionRegistry
from .validation_service import ValidationService
from .temporal_service import TemporalService

__all__ = [
    # Core models
    'Rule', 'Facts', 'ExecutionContext', 'ExecutionResult', 'Goal',
    
    # Engine
    'Engine',
    
    # Services
    'RuleLoader', 'ConditionParser', 'FunctionRegistry', 'ValidationService', 'TemporalService',
    
    # Exceptions
    'SymbolicaError', 'ValidationError', 'EvaluationError',
    
    # Interfaces
    'ConditionEvaluator', 'ExecutionStrategy',
    
    # Factories
    'facts', 'goal'
] 