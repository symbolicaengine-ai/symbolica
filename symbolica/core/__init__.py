"""
Symbolica Core Package
=====================

Core domain models and engine for deterministic AI agent reasoning.
"""

from .models import Rule, Facts, ExecutionContext, ExecutionResult, Goal, facts, goal
from .engine import Engine
from .exceptions import SymbolicaError, ValidationError, EvaluationError
from .interfaces import ConditionEvaluator, ExecutionStrategy
from .services.loader import RuleLoader, ConditionParser
from .services.function_registry import FunctionRegistry
from .services.temporal_service import TemporalService
from .validation.validation_service import ValidationService

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