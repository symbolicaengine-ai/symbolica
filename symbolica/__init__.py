"""
Symbolica - Deterministic Rule Engine for AI Agents
==================================================

Replace unpredictable LLM reasoning with deterministic, traceable rule execution.

Key Benefits:
- Deterministic: Same inputs → same outputs, every time  
- Traceable: Full explanation of why decisions were made
- Scalable: Handles 1000+ rules efficiently using dependency analysis
- Fast: Sub-millisecond execution for real-time agent decisions

Quick Start:
    ```python
    from symbolica import Engine
    
    rules = '''
    rules:
      - id: high_value_customer
        priority: 100
        condition: "amount > 1000 and status == 'active'"
        actions:
          tier: premium
          discount: 0.15
    '''
    
    engine = Engine.from_yaml(rules)
    result = engine.reason({"amount": 1500, "status": "active"})
    print(result.verdict)  # {"tier": "premium", "discount": 0.15}
    ```

Advanced Loading:
    ```python
    # From file
    engine = Engine.from_file("rules.yaml")
    
    # From directory (recursive)
    engine = Engine.from_directory("rules/")
    
    # From YAML string
    engine = Engine.from_yaml(yaml_content)
    ```
"""

# Main engine interface
from .engine import Engine, from_yaml

# Core domain models  
from .core import (
    Rule, Facts, ExecutionResult,
    SymbolicaError, ValidationError, ExecutionError,
    facts
)

__version__ = "0.2.0"
__author__ = "Symbolica Team"

# Minimal public API - only what AI agents need
__all__ = [
    # Main interface
    "Engine", 
    "from_yaml",
    
    # Core models
    "Rule",
    "Facts",
    "ExecutionResult",
    
    # Exceptions
    "SymbolicaError",
    "ValidationError", 
    "ExecutionError",
    
    # Metadata
    "__version__",
    "__author__",
    
    # New from_directory import
    "facts"
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
