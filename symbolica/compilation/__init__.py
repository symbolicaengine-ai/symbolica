"""
Symbolica Compilation System
============================

Comprehensive rule compilation pipeline that transforms YAML rules into
optimized internal representations for high-performance execution.

Features:
- YAML rule parsing (single rule and multi-rule formats)
- Rule validation and linting
- Expression parsing and optimization
- Binary rule pack generation
- Dependency analysis and optimization
"""

from .parser import RuleParser, parse_yaml_file, parse_yaml_string
from .compiler import RuleCompiler, compile_rules, compile_directory, CompilationResult
from .optimizer import RuleOptimizer, optimize_rules
from .packager import RulePackager, create_rule_pack
from .validator import RuleValidator, validate_rules

__all__ = [
    # High-level functions
    'compile_rules',
    'compile_directory',
    'create_rule_pack',
    'validate_rules',
    'optimize_rules',
    
    # Core classes
    'RuleParser',
    'RuleCompiler', 
    'RuleOptimizer',
    'RulePackager',
    'RuleValidator',
    'CompilationResult',
    
    # Parser functions
    'parse_yaml_file',
    'parse_yaml_string',
]
