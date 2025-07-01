"""
Symbolica Compiler Module
=========================

Rule compilation pipeline that transforms YAML rules into optimized binary
rule packs for high-performance execution.

This module contains:
- YAML rule parser
- Rule linting and validation
- AST (Abstract Syntax Tree) definitions
- Rule optimization passes
- Binary rulepack generation
"""

from __future__ import annotations

from typing import List, Dict, Any, Union
import pathlib

# Core compiler components
from .parser import parse_yaml, RawRule
from .lint import lint_folder, LintResult  
from .ast import Expr, Pred, And, Or, Not
from .optimiser import optimise
from .packager import build_pack

__all__ = [
    # High-level functions
    "build_pack",
    "lint_folder", 
    "compile_rules",
    
    # Lower-level components
    "parse_yaml",
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
    status_precedence: List[str] = None
) -> Dict[str, Any]:
    """
    High-level function to compile YAML rules into a rulepack.
    
    Args:
        rules_dir: Directory containing YAML rule files
        output_path: Path for the output .rpack file
        lint_first: Whether to lint rules before compilation
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
    from .. import CompilationError
    
    try:
        # Step 1: Lint if requested
        if lint_first:
            lint_errors = lint_folder(rules_dir)
            if lint_errors > 0:
                raise CompilationError(f"Linting failed with {lint_errors} errors")
        
        # Step 2: Compile
        build_pack(
            rules_dir=rules_dir,
            output_path=output_path,
            status_precedence=status_precedence
        )
        
        # Step 3: Gather stats
        output_file = pathlib.Path(output_path)
        file_size = output_file.stat().st_size if output_file.exists() else 0
        
        # Count rules by parsing the directory
        rule_count = 0
        for yaml_file in pathlib.Path(rules_dir).rglob("*.yaml"):
            try:
                parse_yaml(yaml_file)
                rule_count += 1
            except Exception:
                pass  # Already caught by linting
        
        return {
            "success": True,
            "rules_dir": str(rules_dir),
            "output_path": str(output_path),
            "rule_count": rule_count,
            "file_size_bytes": file_size,
            "lint_performed": lint_first
        }
        
    except Exception as e:
        if isinstance(e, CompilationError):
            raise
        raise CompilationError(f"Compilation failed: {e}") from e


def get_compiler_info() -> Dict[str, Any]:
    """Get information about the compiler capabilities."""
    return {
        "supported_operators": ["==", "!=", ">", ">=", "<", "<=", "in", "not in"],
        "supported_ast_nodes": ["Pred", "And", "Or", "Not"],
        "yaml_features": ["string_expressions", "structured_conditions", "priorities", "agents"],
        "optimization_passes": ["priority_sort", "predicate_index", "agent_grouping"]
    } 