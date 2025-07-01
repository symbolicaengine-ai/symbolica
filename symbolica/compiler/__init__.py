"""
Symbolica Compiler Module
=========================

Rule compilation pipeline that transforms YAML rules into optimized binary
rule packs for high-performance execution.

This module contains:
- YAML rule parser (both single rule and multi-rule formats)
- Rule linting and validation
- AST (Abstract Syntax Tree) definitions
- Rule optimization passes
- Binary rulepack generation
- Extensible compiler architecture with stages

Quick Start:
    >>> from symbolica.compiler import create_default_compiler
    >>> compiler = create_default_compiler()
    >>> result = compiler.compile("rules/", "output.rpack")
    >>> print(f"Compiled {result.rule_count} rules")
"""

from __future__ import annotations

from typing import List, Dict, Any, Union
import pathlib

# Core compiler components
from .parser import parse_yaml, parse_yaml_file, RawRule
from .lint import lint_folder, LintResult  
from .ast import Expr, Pred, And, Or, Not
from .optimiser import optimise
from .packager import build_pack
from .expressions import (
    ExpressionParser, 
    parse_expression, 
    evaluate_expression,
    ExpressionNode,
    LiteralNode,
    FieldNode,
    ComparisonNode,
    ArithmeticNode,
    FunctionCallNode,
    BooleanNode
)
from .schema import (
    ValidationResult,
    validate_rule_document,
    get_schema_info
)

# New extensible architecture
from .base import (
    Compiler, 
    CompilerStage, 
    CompilationContext, 
    CompilationResult, 
    RuleProcessor
)
from .stages import (
    ValidationStage,
    ParsingStage, 
    OptimizationStage,
    PackagingStage,
    create_default_compiler,
    create_strict_compiler
)

__all__ = [
    # High-level compiler builders
    "create_default_compiler",
    "create_strict_compiler",
    
    # Extensible architecture
    "Compiler",
    "CompilerStage",
    "CompilationContext", 
    "CompilationResult",
    "RuleProcessor",
    
    # Concrete stages
    "ValidationStage",
    "ParsingStage",
    "OptimizationStage", 
    "PackagingStage",
    
    # Legacy high-level functions
    "build_pack",
    "lint_folder", 
    "compile_rules",
    
    # Lower-level components
    "parse_yaml",
    "parse_yaml_file",
    "optimise",
    
    # AST classes
    "Expr", 
    "Pred",
    "And", 
    "Or",
    "Not",
    
    # Data types
    "RawRule",
    "LintResult",
]


def compile_rules(
    rules_dir: Union[str, pathlib.Path] = "symbolica_rules",
    output_path: Union[str, pathlib.Path] = "rulepack.rpack", 
    lint_first: bool = True,
    strict: bool = False,
    status_precedence: List[str] = None
) -> Dict[str, Any]:
    """
    High-level function to compile YAML rules into a rulepack.
    
    This is the legacy API. For more control, use the extensible compiler:
    
        compiler = create_default_compiler()
        result = compiler.compile(rules_dir, output_path)
    
    Args:
        rules_dir: Directory containing YAML rule files
        output_path: Path for the output .rpack file
        lint_first: Whether to lint rules before compilation
        strict: Whether to treat warnings as errors
        status_precedence: Custom decision status ordering
        
    Returns:
        Compilation statistics and information
        
    Raises:
        CompilationError: If compilation fails
        
    Example:
        >>> from symbolica.compiler import compile_rules
        >>> stats = compile_rules(
        ...     rules_dir="my_rules/",
        ...     output_path="production.rpack",
        ...     lint_first=True
        ... )
        >>> print(f"Compiled {stats['rule_count']} rules")
    """
    from ..core.exceptions import RuleEngineError
    
    try:
        # Use new extensible compiler
        if strict:
            compiler = create_strict_compiler()
        else:
            compiler = create_default_compiler()
        
        # Set up packaging stage with custom precedence
        if status_precedence:
            # Replace packaging stage with custom precedence
            stages = [s for s in compiler.stages if not isinstance(s, PackagingStage)]
            stages.append(PackagingStage(status_precedence))
            compiler.stages = stages
        
        result = compiler.compile(rules_dir, output_path)
        
        if not result.success:
            error_msg = "; ".join(result.errors)
            raise RuleEngineError(f"Compilation failed: {error_msg}")
        
        return {
            "success": True,
            "rules_dir": str(rules_dir),
            "output_path": str(output_path),
            "rule_count": result.rule_count,
            "file_size_bytes": result.file_size or 0,
            "lint_performed": lint_first,
            "errors": result.errors,
            "warnings": result.warnings,
            "stats": result.stats
        }
        
    except Exception as e:
        if isinstance(e, RuleEngineError):
            raise
        raise RuleEngineError(f"Compilation failed: {e}") from e


def get_compiler_info() -> Dict[str, Any]:
    """Get information about the compiler capabilities."""
    return {
        "supported_operators": {
            "comparison": ["==", "!=", ">", ">=", "<", "<="],
            "membership": ["in", "not in"],
            "arithmetic": ["+", "-", "*", "/", "%"],
            "boolean": ["all", "any", "not"]
        },
        "supported_functions": {
            "string_helpers": ["startswith", "endswith", "contains"]
        },
        "supported_features": {
            "null_checks": ["field == null", "field != null"],
            "parentheses": True,
            "list_literals": True,
            "nested_expressions": True
        },
        "expression_formats": [
            "string_expressions",      # "amount > 1000"
            "structured_yaml",         # { all: [...] }
            "mixed_expressions"        # [ "expr", { any: [...] } ]
        ],
        "supported_ast_nodes": [
            "Pred", "And", "Or", "Not", 
            "LiteralNode", "FieldNode", "ComparisonNode", 
            "ArithmeticNode", "FunctionCallNode", "BooleanNode"
        ],
        "yaml_features": ["string_expressions", "structured_conditions", "priorities", "agents"],
        "optimization_passes": ["priority_sort", "predicate_index", "agent_grouping"],
        "rule_formats": ["single_rule", "multi_rule_array"],
        "compiler_stages": ["validation", "parsing", "optimization", "packaging"],
        "extensible": True,
        "comprehensive_expressions": True
    } 