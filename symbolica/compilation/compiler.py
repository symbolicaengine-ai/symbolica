"""
Rule Compiler
============

Main compilation orchestrator that transforms YAML rules into 
optimized internal representations for execution.

Features:
- YAML parsing and validation
- Expression optimization
- Dependency analysis
- Rule optimization
- Error reporting and debugging
"""

import pathlib
import json
from typing import List, Dict, Any, Union, Optional
from dataclasses import dataclass

from ..core import RuleSet, ValidationError, CompilationError
from .parser import RuleParser, parse_yaml_directory, RuleParseResult
from .._internal.evaluator import create_evaluator


@dataclass
class CompilationResult:
    """Result of rule compilation process."""
    success: bool
    rule_set: Optional[RuleSet]
    errors: List[str]
    warnings: List[str]
    stats: Dict[str, Any]


class RuleCompiler:
    """
    Main rule compiler that orchestrates the compilation process.
    
    Features:
    - Parses YAML rules from files or directories
    - Validates expressions and dependencies
    - Optimizes rule execution order
    - Generates compiled rule sets
    """
    
    def __init__(self, strict: bool = False, optimize: bool = True):
        self.strict = strict
        self.optimize = optimize
        self.parser = RuleParser(strict=strict)
        self.evaluator = create_evaluator()
    
    def compile_file(self, file_path: Union[str, pathlib.Path]) -> CompilationResult:
        """Compile rules from a single YAML file."""
        parse_result = self.parser.parse_file(file_path)
        return self._process_parse_result(parse_result)
    
    def compile_directory(self, directory: Union[str, pathlib.Path]) -> CompilationResult:
        """Compile all YAML rules in a directory."""
        parse_result = parse_yaml_directory(directory, strict=self.strict)
        return self._process_parse_result(parse_result)
    
    def compile_string(self, yaml_content: str) -> CompilationResult:
        """Compile rules from YAML string."""
        parse_result = self.parser.parse_string(yaml_content)
        return self._process_parse_result(parse_result)
    
    def compile_rules(self, rules: List[Dict[str, Any]]) -> CompilationResult:
        """Compile rules from pre-parsed rule dictionaries."""
        errors = []
        warnings = []
        parsed_rules = []
        
        for i, rule_data in enumerate(rules):
            try:
                rule = self.parser._parse_single_rule(rule_data, context=f"rule[{i}]")
                parsed_rules.append(rule)
            except Exception as e:
                errors.append(f"Error parsing rule[{i}]: {e}")
                if self.strict:
                    break
        
        parse_result = RuleParseResult(
            rules=parsed_rules,
            errors=errors,
            warnings=warnings
        )
        
        return self._process_parse_result(parse_result)
    
    def _process_parse_result(self, parse_result: RuleParseResult) -> CompilationResult:
        """Process parsed rules and generate compilation result."""
        errors = parse_result.errors.copy()
        warnings = parse_result.warnings.copy()
        
        if parse_result.errors and self.strict:
            return CompilationResult(
                success=False,
                rule_set=None,
                errors=errors,
                warnings=warnings,
                stats={'parsed_rules': 0, 'valid_rules': 0}
            )
        
        if not parse_result.rules:
            errors.append("No valid rules found")
            return CompilationResult(
                success=False,
                rule_set=None,
                errors=errors,
                warnings=warnings,
                stats={'parsed_rules': 0, 'valid_rules': 0}
            )
        
        # Validate expressions and extract field dependencies
        valid_rules = []
        for rule in parse_result.rules:
            try:
                # Validate expression by attempting to extract fields
                self.evaluator.extract_fields(rule.condition)
                valid_rules.append(rule)
            except Exception as e:
                error_msg = f"Invalid expression in rule '{rule.id.value}': {e}"
                if self.strict:
                    errors.append(error_msg)
                else:
                    warnings.append(error_msg)
        
        if not valid_rules:
            errors.append("No rules with valid expressions found")
            return CompilationResult(
                success=False,
                rule_set=None,
                errors=errors,
                warnings=warnings,
                stats={'parsed_rules': len(parse_result.rules), 'valid_rules': 0}
            )
        
        # Create rule set with metadata
        try:
            rule_set = RuleSet(
                rules=valid_rules,
                metadata={
                    'compiled_at': json.dumps({'timestamp': str(pathlib.Path.cwd())}),
                    'compiler_version': '1.0.0',
                    'optimization_enabled': self.optimize,
                    'strict_mode': self.strict
                }
            )
            
            # Generate compilation statistics
            stats = self._generate_stats(rule_set, parse_result)
            
            return CompilationResult(
                success=len(errors) == 0,
                rule_set=rule_set,
                errors=errors,
                warnings=warnings,
                stats=stats
            )
            
        except Exception as e:
            errors.append(f"Failed to create rule set: {e}")
            return CompilationResult(
                success=False,
                rule_set=None,
                errors=errors,
                warnings=warnings,
                stats={'parsed_rules': len(parse_result.rules), 'valid_rules': len(valid_rules)}
            )
    
    def _generate_stats(self, rule_set: RuleSet, parse_result: RuleParseResult) -> Dict[str, Any]:
        """Generate compilation statistics."""
        
        # Basic stats
        stats = {
            'parsed_rules': len(parse_result.rules),
            'valid_rules': rule_set.rule_count,
            'total_errors': len(parse_result.errors),
            'total_warnings': len(parse_result.warnings)
        }
        
        # Priority distribution
        priorities = [rule.priority.value for rule in rule_set.rules]
        stats['priority_range'] = {
            'min': min(priorities) if priorities else 0,
            'max': max(priorities) if priorities else 0,
            'average': sum(priorities) / len(priorities) if priorities else 0
        }
        
        # Field usage analysis
        all_read_fields = set()
        all_write_fields = set()
        
        for rule in rule_set.rules:
            all_read_fields.update(rule.referenced_fields)
            all_write_fields.update(rule.written_fields)
        
        stats['field_usage'] = {
            'total_read_fields': len(all_read_fields),
            'total_write_fields': len(all_write_fields),
            'overlapping_fields': len(all_read_fields & all_write_fields)
        }
        
        # Expression complexity analysis
        expression_lengths = [len(rule.condition.expression) for rule in rule_set.rules]
        stats['expression_complexity'] = {
            'average_length': sum(expression_lengths) / len(expression_lengths) if expression_lengths else 0,
            'max_length': max(expression_lengths) if expression_lengths else 0
        }
        
        # Tag analysis
        all_tags = set()
        for rule in rule_set.rules:
            all_tags.update(rule.tags)
        
        stats['tags'] = {
            'unique_tags': len(all_tags),
            'tagged_rules': sum(1 for rule in rule_set.rules if rule.tags)
        }
        
        return stats


# Convenience functions
def compile_rules(source: Union[str, pathlib.Path, List[Dict[str, Any]]], 
                 strict: bool = False, 
                 optimize: bool = True) -> CompilationResult:
    """
    Compile rules from various sources.
    
    Args:
        source: File path, directory path, or list of rule dictionaries
        strict: Enable strict validation mode
        optimize: Enable optimization passes
    
    Returns:
        CompilationResult with success status and compiled rules
    """
    compiler = RuleCompiler(strict=strict, optimize=optimize)
    
    if isinstance(source, list):
        return compiler.compile_rules(source)
    
    source_path = pathlib.Path(source)
    
    if source_path.is_file():
        return compiler.compile_file(source_path)
    elif source_path.is_dir():
        return compiler.compile_directory(source_path)
    else:
        # Try as YAML string
        try:
            return compiler.compile_string(str(source))
        except Exception as e:
            return CompilationResult(
                success=False,
                rule_set=None,
                errors=[f"Invalid source: {source} - {e}"],
                warnings=[],
                stats={}
            )


def compile_directory(directory: Union[str, pathlib.Path], 
                     strict: bool = False, 
                     optimize: bool = True) -> CompilationResult:
    """Compile all YAML files in a directory."""
    compiler = RuleCompiler(strict=strict, optimize=optimize)
    return compiler.compile_directory(directory)


def validate_rules(source: Union[str, pathlib.Path, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Validate rules without full compilation.
    
    Returns:
        Validation report with errors, warnings, and basic stats
    """
    result = compile_rules(source, strict=False, optimize=False)
    
    return {
        'valid': result.success,
        'errors': result.errors,
        'warnings': result.warnings,
        'rule_count': result.stats.get('valid_rules', 0),
        'stats': result.stats
    } 