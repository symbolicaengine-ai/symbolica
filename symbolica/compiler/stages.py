"""
symbolica.compiler.stages
========================

Concrete compiler stages for the Symbolica compilation pipeline.
"""

from __future__ import annotations

import pathlib
from typing import Any, Dict, List

from .base import CompilerStage, CompilationContext  
from .parser import parse_yaml_file
from .lint import lint_folder
from .packager import build_pack
from .optimiser import optimise


class ValidationStage(CompilerStage):
    """Stage that validates rule files using the linter."""
    
    def __init__(self, strict: bool = False):
        super().__init__("Validation")
        self.strict = strict
    
    def process(self, context: CompilationContext) -> bool:
        """Run linting validation on all rule files."""
        try:
            error_count = lint_folder(context.rules_dir, strict=self.strict)
            
            if error_count > 0:
                self.add_error(context, f"Validation failed with {error_count} errors")
                return False
            
            context.stats['validation_passed'] = True
            return True
            
        except Exception as e:
            self.add_error(context, f"Validation stage failed: {e}")
            return False


class ParsingStage(CompilerStage):
    """Stage that parses all YAML files into RawRule objects."""
    
    def __init__(self):
        super().__init__("Parsing")
    
    def process(self, context: CompilationContext) -> bool:
        """Parse all YAML files in rules directory."""
        try:
            raw_rules = []
            file_count = 0
            
            for yaml_file in context.rules_dir.rglob("*.yaml"):
                try:
                    file_rules = parse_yaml_file(yaml_file)
                    raw_rules.extend(file_rules)
                    file_count += 1
                except Exception as e:
                    self.add_error(context, f"Failed to parse {yaml_file}: {e}")
                    return False
            
            # Store parsed rules in context
            context.stats['raw_rules'] = raw_rules
            context.stats['rule_count'] = len(raw_rules)
            context.stats['file_count'] = file_count
            
            if len(raw_rules) == 0:
                self.add_warning(context, "No rules found in directory")
            
            return True
            
        except Exception as e:
            self.add_error(context, f"Parsing stage failed: {e}")
            return False


class OptimizationStage(CompilerStage):
    """Stage that optimizes rules for runtime performance."""
    
    def __init__(self):
        super().__init__("Optimization")
    
    def process(self, context: CompilationContext) -> bool:
        """Optimize rules for runtime execution."""
        try:
            raw_rules = context.stats.get('raw_rules', [])
            if not raw_rules:
                self.add_error(context, "No rules to optimize")
                return False
            
            # Convert RawRule objects to dict format for optimizer
            rule_dicts = []
            for raw_rule in raw_rules:
                rule_dict = {
                    "id": raw_rule["id"],
                    "priority": raw_rule["priority"], 
                    "agent": raw_rule["agent"],
                    "if": raw_rule["if_"],
                    "then": raw_rule["then"],
                    "tags": raw_rule["tags"]
                }
                rule_dicts.append(rule_dict)
            
            # Run optimization
            sorted_rules, predicate_index = optimise(rule_dicts)
            
            # Store optimized results
            context.stats['optimized_rules'] = sorted_rules
            context.stats['predicate_index'] = predicate_index
            context.stats['optimization_passed'] = True
            
            return True
            
        except Exception as e:
            self.add_error(context, f"Optimization stage failed: {e}")
            return False


class PackagingStage(CompilerStage):
    """Stage that packages optimized rules into .rpack file."""
    
    def __init__(self, status_precedence: List[str] = None):
        super().__init__("Packaging")
        self.status_precedence = status_precedence
    
    def process(self, context: CompilationContext) -> bool:
        """Package optimized rules into binary format."""
        try:
            optimized_rules = context.stats.get('optimized_rules')
            predicate_index = context.stats.get('predicate_index')
            
            if optimized_rules is None or predicate_index is None:
                self.add_error(context, "No optimized rules available for packaging")
                return False
            
            # Use the existing build_pack function
            build_pack(
                rules_dir=context.rules_dir,
                output_path=context.output_path,
                status_precedence=self.status_precedence
            )
            
            # Verify output was created
            if not context.output_path.exists():
                self.add_error(context, f"Output file was not created: {context.output_path}")
                return False
            
            context.stats['packaging_passed'] = True
            context.stats['output_size'] = context.output_path.stat().st_size
            
            return True
            
        except Exception as e:
            self.add_error(context, f"Packaging stage failed: {e}")
            return False


def create_default_compiler():
    """Create a compiler with the standard pipeline stages."""
    from .base import Compiler
    
    return (Compiler()
            .add_stage(ValidationStage(strict=False))
            .add_stage(ParsingStage()) 
            .add_stage(OptimizationStage())
            .add_stage(PackagingStage()))


def create_strict_compiler():
    """Create a compiler with strict validation."""
    from .base import Compiler
    
    return (Compiler()
            .add_stage(ValidationStage(strict=True))
            .add_stage(ParsingStage())
            .add_stage(OptimizationStage()) 
            .add_stage(PackagingStage())) 