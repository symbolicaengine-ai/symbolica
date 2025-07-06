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
from .dag import build_execution_dag


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
    """Stage that optimizes rules for runtime performance using DAG."""
    
    def __init__(self, enable_dag: bool = True):
        super().__init__("Optimization")
        self.enable_dag = enable_dag
    
    def process(self, context: CompilationContext) -> bool:
        """Optimize rules for runtime execution using DAG analysis."""
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
            
            if self.enable_dag:
                # Build ExecutionDAG with enhanced features
                try:
                    execution_dag = build_execution_dag(rule_dicts)
                    context.stats['execution_dag'] = execution_dag
                    context.stats['dag_optimization_enabled'] = True
                    
                    # Also provide legacy format for backward compatibility
                    sorted_rules, predicate_index = optimise(rule_dicts)
                    context.stats['optimized_rules'] = sorted_rules
                    context.stats['predicate_index'] = predicate_index
                    
                except Exception as e:
                    self.add_warning(context, f"DAG optimization failed, falling back to legacy: {e}")
                    # Fallback to legacy optimization
                    sorted_rules, predicate_index = optimise(rule_dicts)
                    context.stats['optimized_rules'] = sorted_rules
                    context.stats['predicate_index'] = predicate_index
                    context.stats['dag_optimization_enabled'] = False
            else:
                # Legacy optimization only
                sorted_rules, predicate_index = optimise(rule_dicts)
                context.stats['optimized_rules'] = sorted_rules
                context.stats['predicate_index'] = predicate_index
                context.stats['dag_optimization_enabled'] = False
            
            context.stats['optimization_passed'] = True
            return True
            
        except Exception as e:
            self.add_error(context, f"Optimization stage failed: {e}")
            return False


class PackagingStage(CompilerStage):
    """Stage that packages optimized rules into .rpack file with DAG support."""
    
    def __init__(self, status_precedence: List[str] = None, enable_dag: bool = True):
        super().__init__("Packaging")
        self.status_precedence = status_precedence
        self.enable_dag = enable_dag
    
    def process(self, context: CompilationContext) -> bool:
        """Package optimized rules into binary format with DAG support."""
        try:
            optimized_rules = context.stats.get('optimized_rules')
            predicate_index = context.stats.get('predicate_index')
            execution_dag = context.stats.get('execution_dag')
            dag_enabled = context.stats.get('dag_optimization_enabled', False)
            
            if optimized_rules is None or predicate_index is None:
                self.add_error(context, "No optimized rules available for packaging")
                return False
            
            # Use DAG-aware packaging
            if self.enable_dag and dag_enabled and execution_dag:
                from .packager import build_pack_dag
                build_pack_dag(
                    rules_dir=context.rules_dir,
                    output_path=context.output_path,
                    status_precedence=self.status_precedence
                )
                context.stats['version'] = "dag"
            else:
                # Fallback to legacy packaging
                from .packager import build_pack_legacy
                build_pack_legacy(
                    rules_dir=context.rules_dir,
                    output_path=context.output_path,
                    status_precedence=self.status_precedence
                )
                context.stats['version'] = "legacy"
            
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
    """Create a compiler with the standard pipeline stages (DAG-enabled)."""
    from .base import Compiler
    
    return (Compiler()
            .add_stage(ValidationStage(strict=False))
            .add_stage(ParsingStage()) 
            .add_stage(OptimizationStage(enable_dag=True))
            .add_stage(PackagingStage(enable_dag=True)))


def create_strict_compiler():
    """Create a compiler with strict validation (DAG-enabled)."""
    from .base import Compiler
    
    return (Compiler()
            .add_stage(ValidationStage(strict=True))
            .add_stage(ParsingStage())
            .add_stage(OptimizationStage(enable_dag=True)) 
            .add_stage(PackagingStage(enable_dag=True)))


def create_legacy_compiler():
    """Create a compiler with legacy pipeline (no DAG)."""
    from .base import Compiler
    
    return (Compiler()
            .add_stage(ValidationStage(strict=False))
            .add_stage(ParsingStage())
            .add_stage(OptimizationStage(enable_dag=False)) 
            .add_stage(PackagingStage(enable_dag=False))) 