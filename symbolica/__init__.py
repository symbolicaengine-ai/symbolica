"""
Symbolica - Enhanced Rule Engine for AI Agents
==============================================

A high-performance, dependency-aware rule engine optimized for AI applications.

Features:
- Comprehensive expression evaluation (Python-like syntax + structured YAML)
- YAML rule compilation with validation and optimization
- DAG-based parallel execution with automatic dependency analysis
- Multiple execution strategies (linear, optimized, DAG)
- Content-based caching for performance
- Clean APIs for AI frameworks (LangChain, Semantic Kernel, etc.)

Quick Start:
    ```python
    from symbolica import Engine, from_yaml
    
    # From YAML string
    engine = from_yaml('''
    rules:
      - id: high_value
        if: "amount > 1000 and status == 'active'"
        then:
          set:
            tier: premium
            discount: 0.15
    ''')
    
    # Reason about facts
    result = engine.reason({
        'amount': 1500,
        'status': 'active'
    })
    
    print(result.verdict)  # {'tier': 'premium', 'discount': 0.15}
    ```

Architecture:
    - engine/: Main inference engine for AI agents
    - compilation/: YAML parsing, validation, and compilation
    - core/: Domain models and interfaces
    - _internal/: High-performance implementation details
"""

# Main engine interface
from .engine import Engine, from_yaml, quick_reason, create_simple_rule

# Core domain models  
from .core import (
    # Data models
    Rule, RuleSet, Facts, ExecutionResult, ExecutionContext,
    Priority, Condition, Action, RuleId,
    
    # Factory functions
    rule_id, priority, condition, action_set, action_call, facts,
    
    # Exceptions
    SymbolicaError, ValidationError, CompilationError, 
    ExecutionError, EvaluationError, LoadError,
    
    # Interfaces (for advanced users)
    ConditionEvaluator, ActionExecutor, ExecutionStrategy,
    
    # Enums
    TraceLevel
)

# Compilation system (for advanced usage)
from .compilation import (
    # High-level functions
    compile_rules, validate_rules, optimize_rules,
    
    # Core classes
    RuleCompiler, RuleValidator, RuleOptimizer,
    
    # Parser functions
    parse_yaml_file, parse_yaml_string
)


__version__ = "1.0.0"
__author__ = "Symbolica Team"

__all__ = [
    # Main interface - most users only need these
    "Engine", 
    "from_yaml", 
    "quick_reason",
    "create_simple_rule",
    
    # Core models
    "Rule",
    "RuleSet", 
    "Facts",
    "ExecutionResult",
    "Priority",
    "Condition", 
    "Action",
    "RuleId",
    
    # Factory functions
    "rule_id",
    "priority", 
    "condition",
    "action_set",
    "action_call",
    "facts",
    
    # Exceptions
    "SymbolicaError",
    "ValidationError", 
    "CompilationError",
    "ExecutionError",
    "EvaluationError",
    "LoadError",
    
    # Compilation (advanced)
    "compile_rules",
    "validate_rules",
    "optimize_rules",
    "RuleCompiler",
    "RuleValidator", 
    "RuleOptimizer",
    "parse_yaml_file",
    "parse_yaml_string",
    
    # Interfaces (advanced)
    "ConditionEvaluator",
    "ActionExecutor", 
    "ExecutionStrategy",
    "ExecutionContext",
    "TraceLevel",
    
    # Metadata
    "__version__",
    "__author__"
]


# Package information for tooling
def get_info():
    """Get package information."""
    return {
        "name": "symbolica",
        "version": __version__,
        "description": "Enhanced rule engine for AI agents",
        "features": [
            "Comprehensive expression evaluation",
            "YAML compilation and validation", 
            "DAG-based parallel execution",
            "Multiple execution strategies",
            "Content-based caching",
            "AI framework integration"
        ],
        "supported_expressions": {
            "comparison": ["==", "!=", ">", ">=", "<", "<=", "in", "not in"],
            "arithmetic": ["+", "-", "*", "/", "%", "**"],
            "boolean": ["and", "or", "not", "all", "any"],
            "string": ["startswith", "endswith", "contains", "matches"],
            "functions": ["len", "sum", "abs", "min", "max", "str", "int", "float"],
            "null_checks": ["== None", "!= None", "is_null", "is_not_null"]
        },
        "execution_strategies": ["linear", "optimized", "dag", "auto"],
        "yaml_formats": ["single_rule", "multi_rule", "structured_expressions"]
    }
