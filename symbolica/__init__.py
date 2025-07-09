"""
Symbolica: Deterministic Rule Engine for AI Agents
==================================================

Simple, focused rule engine providing deterministic, explainable reasoning
for AI agents. Clean architecture without overengineering.

Core Features:
- YAML-based rule definition with flexible syntax
- Simple explanations for AI agents
- DAG-based dependency resolution
- Fast AST-based expression evaluation

Example Usage:
    from symbolica import Engine, facts
    
    # Create engine from YAML
    engine = Engine.from_yaml('''
    rules:
      - id: high_value_customer
        condition: purchase_amount > 1000
        actions:
            tier: premium
          discount: 0.1
    ''')
    
    # Execute with simple explanation
    result = engine.reason(facts(purchase_amount=1500))
    
    # Get clean reasoning
    print(result.reasoning)
    
    # Get LLM-friendly context
    llm_context = result.get_llm_context()
"""

from .core import (
    # Core models
    Rule, Facts, ExecutionContext, ExecutionResult, Goal,
    
    # Engine
    Engine,
    
    # Exceptions
    SymbolicaError, ValidationError, EvaluationError,
    
    # Factories
    facts, goal
)

# For backward compatibility
from_yaml = Engine.from_yaml

__version__ = "0.0.3"
__author__ = "Symbolica Team"

# Minimal public API - only what AI agents need
__all__ = [
    # Core models
    'Rule', 'Facts', 'ExecutionContext', 'ExecutionResult', 'Goal',
    
    # Engine
    'Engine',
    
    # Exceptions
    'SymbolicaError', 'ValidationError', 'EvaluationError',
    
    # Factories
    'facts', 'goal', 'from_yaml',
    
    # Metadata
    '__version__',
    '__author__'
]


def get_info():
    """Get package information."""
    return {
        "name": "symbolica",
        "version": __version__,
        "description": "Deterministic rule engine for AI agents",
        "core_features": [
            "YAML rule parsing",
            "AST-based expression evaluation", 
            "DAG execution for 1000+ rules",
            "Deterministic reasoning",
            "AI agent traceability"
        ],
        "use_cases": [
            "Replace LLM reasoning with deterministic logic",
            "Ensure consistent AI agent decisions", 
            "Provide explainable AI decision paths",
            "Scale rule processing efficiently"
        ]
    }
