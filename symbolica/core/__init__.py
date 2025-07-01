"""
symbolica.core
=============

Core classes for Symbolica reasoning engine.
"""

from .engine import SymbolicaEngine
from .result import Result
from .exceptions import SymbolicaError, RuleEngineError, RegistryNotFoundError, ValidationError

__all__ = [
    "SymbolicaEngine",
    "Result", 
    "SymbolicaError",
    "RuleEngineError",
    "RegistryNotFoundError",
    "ValidationError"
] 