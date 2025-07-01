"""
Symbolica - Deterministic Reasoning Engine
==========================================

A general purpose deterministic reasoning engine that uses rules to provide
business logic grounding to AI applications.

Quick Start:
    >>> from symbolica import SymbolicaEngine
    >>> 
    >>> # Initialize engine with all business rules
    >>> engine = SymbolicaEngine("business_rules/")
    >>> 
    >>> # Agent calls engine with their registry
    >>> result = engine.infer(
    ...     facts={"amount": 1500, "country": "RU"}, 
    ...     rules="fraud_detector.reg.yaml"
    ... )
    >>> 
    >>> # Agent processes result and trace
    >>> print(result.status, result.reason)
    >>> # Agent decides what to do with: result.trace
"""

import sys

# Version information
__version__ = "0.2.0"

# Minimum Python version check
if sys.version_info < (3, 8):
    raise RuntimeError("Symbolica requires Python 3.8 or higher")

# Import main classes from core modules
from .core import SymbolicaEngine, Result, SymbolicaError, RuleEngineError, RegistryNotFoundError
from .utils import quick_infer, compile_rules

# Clean exports
__all__ = [
    # Core classes
    "SymbolicaEngine",
    "Result",
    
    # Utilities
    "quick_infer",
    "compile_rules",
    
    # Exceptions
    "SymbolicaError",
    "RuleEngineError",
    "RegistryNotFoundError",
    
    # Version
    "__version__"
]