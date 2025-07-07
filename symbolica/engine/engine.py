"""
Symbolica Engine
===============

Simplified, focused engine for deterministic AI agent reasoning.

Features:
- Direct YAML rule parsing (no complex compilation)
- AST-based expression evaluation  
- DAG execution for 1000+ rules
- Simple traceability for AI agents
"""

import time
import yaml
from typing import Dict, Any, List, Union, Set
from pathlib import Path

from ..core import (
    Rule, Facts, ExecutionResult, ExecutionContext, 
    SymbolicaError, ValidationError, facts
)
from .._internal.evaluator import create_evaluator
from .._internal.dag import create_dag_strategy


class SimpleActionExecutor:
    """Simple action executor that just sets key-value pairs."""
    
    def execute(self, actions: Dict[str, Any], context: ExecutionContext) -> None:
        """Execute actions by setting facts in context."""
        for key, value in actions.items():
            context.set_fact(key, value)


class Engine:
    """
    Main inference engine for AI agents.
    
    Simplified design focused on:
    - Deterministic reasoning (same inputs → same outputs)
    - Efficient DAG execution for 1000+ rules  
    - AI agent traceability and explainability
    """
    
    def __init__(self):
        """Initialize the engine."""
        self._rules: List[Rule] = []
        self._evaluator = create_evaluator()
        self._executor = SimpleActionExecutor()
        self._dag_strategy = create_dag_strategy()
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> 'Engine':
        """Create engine from YAML rules string."""
        engine = cls()
        engine.load_yaml(yaml_content)
        return engine
    
    @classmethod  
    def from_file(cls, file_path: Union[str, Path]) -> 'Engine':
        """Create engine from YAML file."""
        engine = cls()
        engine.load_file(file_path)
        return engine
    
    @classmethod
    def from_directory(cls, directory_path: Union[str, Path], pattern: str = "*.yaml") -> 'Engine':
        """Create engine from directory with recursive YAML search."""
        engine = cls()
        engine.load_directory(directory_path, pattern)
        return engine
    
    def load_yaml(self, yaml_content: str) -> None:
        """Load rules from YAML string."""
        try:
            data = yaml.safe_load(yaml_content)
            self._rules = self._parse_rules(data)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML: {e}")
        except Exception as e:
            raise ValidationError(f"Failed to parse rules: {e}")
    
    def load_file(self, file_path: Union[str, Path]) -> None:
        """Load rules from YAML file."""
        path = Path(file_path)
        if not path.exists():
            raise ValidationError(f"File not found: {file_path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.load_yaml(f.read())
        except Exception as e:
            raise ValidationError(f"Failed to load file {file_path}: {e}")
    
    def load_directory(self, directory_path: Union[str, Path], pattern: str = "*.yaml") -> None:
        """Load rules from all YAML files in directory recursively."""
        dir_path = Path(directory_path)
        if not dir_path.exists():
            raise ValidationError(f"Directory not found: {directory_path}")
        if not dir_path.is_dir():
            raise ValidationError(f"Path is not a directory: {directory_path}")
        
        # Find all YAML files recursively
        yaml_files = []
        for ext in [pattern, pattern.replace('.yaml', '.yml')]:
            yaml_files.extend(dir_path.rglob(ext))
        
        if not yaml_files:
            raise ValidationError(f"No YAML files found in directory: {directory_path}")
        
        # Load and merge all rules
        all_rules = []
        rule_ids = set()
        
        for yaml_file in sorted(yaml_files):  # Sort for consistent ordering
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f.read())
                    
                file_rules = self._parse_rules(data)
                
                # Check for duplicate rule IDs across files
                for rule in file_rules:
                    if rule.id in rule_ids:
                        raise ValidationError(f"Duplicate rule ID '{rule.id}' found in {yaml_file}")
                    rule_ids.add(rule.id)
                    
                all_rules.extend(file_rules)
                
            except Exception as e:
                raise ValidationError(f"Failed to load file {yaml_file}: {e}")
        
        # Sort by priority (highest first)
        all_rules.sort(key=lambda r: r.priority, reverse=True)
        self._rules = all_rules
    
    def _parse_rules(self, data: Dict[str, Any]) -> List[Rule]:
        """Parse YAML data into Rule objects."""
        if not isinstance(data, dict) or 'rules' not in data:
            raise ValidationError("YAML must contain 'rules' key")
        
        rules = []
        rule_ids = set()
        
        for i, rule_data in enumerate(data['rules']):
            try:
                rule = self._parse_single_rule(rule_data)
                
                # Check for duplicate IDs
                if rule.id in rule_ids:
                    raise ValidationError(f"Duplicate rule ID: {rule.id}")
                rule_ids.add(rule.id)
                
                rules.append(rule)
                
            except Exception as e:
                raise ValidationError(f"Error parsing rule {i+1}: {e}")
        
        if not rules:
            raise ValidationError("No valid rules found")
        
        # Sort by priority (highest first)
        rules.sort(key=lambda r: r.priority, reverse=True)
        return rules
    
    def _parse_single_rule(self, rule_data: Dict[str, Any]) -> Rule:
        """Parse a single rule from YAML data."""
        if not isinstance(rule_data, dict):
            raise ValidationError("Rule must be a dictionary")
        
        # Required fields
        rule_id = rule_data.get('id')
        if not rule_id:
            raise ValidationError("Rule must have 'id' field")
        
        condition_data = rule_data.get('condition') or rule_data.get('if')
        if not condition_data:
            raise ValidationError("Rule must have 'condition' or 'if' field")
        
        # Parse condition - can be string or structured
        condition = self._parse_condition(condition_data)
        
        actions_data = rule_data.get('actions') or rule_data.get('then')
        if not actions_data:
            raise ValidationError("Rule must have 'actions' or 'then' field")
        
        # Optional fields  
        priority = rule_data.get('priority', 50)
        tags = rule_data.get('tags', [])
        
        # Parse actions
        if isinstance(actions_data, dict):
            if 'set' in actions_data:
                # Nested set format: then: {set: {key: value}}
                actions = actions_data['set']
            else:
                # Direct key-value actions
                actions = actions_data
        else:
            raise ValidationError("Actions must be a dictionary of key-value pairs")
        
        return Rule(
            id=str(rule_id),
            priority=int(priority),
            condition=condition,
            actions=actions,
            tags=tags if isinstance(tags, list) else []
        )
    
    def _parse_condition(self, condition_data) -> str:
        """Parse condition data - handles both string and structured formats."""
        if isinstance(condition_data, str):
            # Simple string condition
            return condition_data
        elif isinstance(condition_data, dict):
            # Structured condition with all/any/not
            return self._parse_structured_condition(condition_data)
        else:
            raise ValidationError("Condition must be a string or structured object")
    
    def _parse_structured_condition(self, condition_dict: Dict[str, Any]) -> str:
        """Parse structured condition (all/any/not) into expression string."""
        if 'all' in condition_dict:
            # All conditions must be true: "cond1 and cond2 and cond3"
            sub_conditions = condition_dict['all']
            if not isinstance(sub_conditions, list):
                raise ValidationError("'all' must contain a list of conditions")
            
            parsed_conditions = []
            for sub_cond in sub_conditions:
                parsed_conditions.append(f"({self._parse_condition(sub_cond)})")
            
            return " and ".join(parsed_conditions)
            
        elif 'any' in condition_dict:
            # Any condition can be true: "cond1 or cond2 or cond3"
            sub_conditions = condition_dict['any']
            if not isinstance(sub_conditions, list):
                raise ValidationError("'any' must contain a list of conditions")
                
            parsed_conditions = []
            for sub_cond in sub_conditions:
                parsed_conditions.append(f"({self._parse_condition(sub_cond)})")
            
            return " or ".join(parsed_conditions)
            
        elif 'not' in condition_dict:
            # Negate condition: "not (condition)"
            sub_condition = condition_dict['not']
            parsed_condition = self._parse_condition(sub_condition)
            return f"not ({parsed_condition})"
            
        else:
            raise ValidationError("Structured condition must contain 'all', 'any', or 'not'")
    
    def reason(self, facts_data: Dict[str, Any]) -> ExecutionResult:
        """
        Perform reasoning - main method for AI agents.
        
        Args:
            facts_data: Input facts to reason about
            
        Returns:
            ExecutionResult with verdict and trace for AI explainability
        """
        if not isinstance(facts_data, dict):
            raise ValidationError("Facts must be a dictionary")
        
        if not self._rules:
            raise SymbolicaError("No rules loaded. Call load_yaml() or load_file() first")
        
        start_time = time.perf_counter()
        
        try:
            # Create execution context
            input_facts = facts(**facts_data)
            context = ExecutionContext(
                original_facts=input_facts,
                enriched_facts={},
                fired_rules=[]
            )
            
            # Execute rules using DAG strategy for efficiency
            self._execute_rules_dag(context)
            
            # Calculate execution time
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            
            # Create trace for AI agent explainability
            trace = {
                "fired_rules": context.fired_rules,
                "execution_order": context.fired_rules,  # Simple for now
                "total_rules": len(self._rules),
                "execution_time_ms": execution_time_ms
            }
            
            return ExecutionResult(
                verdict=context.verdict,
                fired_rules=context.fired_rules,
                execution_time_ms=execution_time_ms,
                trace=trace
            )
            
        except Exception as e:
            if isinstance(e, SymbolicaError):
                raise
            raise SymbolicaError(f"Reasoning failed: {e}") from e
    
    def _execute_rules_dag(self, context: ExecutionContext) -> None:
        """Execute rules using DAG strategy for dependency awareness."""
        # For now, use simple priority-based execution
        # TODO: Integrate with simplified DAG execution from _internal/dag.py
        
        for rule in self._rules:
            try:
                # Evaluate condition
                if self._evaluator.evaluate(rule.condition, context):
                    # Rule fired - execute actions
                    context.rule_fired(rule.id)
                    self._executor.execute(rule.actions, context)
                    
            except Exception as e:
                # Log error but continue execution for robustness
                # In production, you might want proper logging here
                continue
    
    def test_condition(self, expression: str, facts_data: Dict[str, Any]) -> bool:
        """
        Test a condition against facts (useful for debugging).
        
        Args:
            expression: Condition expression to test
            facts_data: Facts to test against
            
        Returns:
            True if condition is satisfied
        """
        input_facts = facts(**facts_data)
        context = ExecutionContext(
            original_facts=input_facts,
            enriched_facts={},
            fired_rules=[]
        )
        
        return self._evaluator.evaluate(expression, context)
    
    def get_analysis(self) -> Dict[str, Any]:
        """Get analysis of loaded rules for monitoring."""
        return {
            'rule_count': len(self._rules),
            'rule_ids': [rule.id for rule in self._rules],
            'avg_priority': sum(rule.priority for rule in self._rules) / len(self._rules) if self._rules else 0
        }
    
    def explain_last_execution(self) -> Dict[str, Any]:
        """Get explanation of last execution (placeholder for AI traceability)."""
        # This would be populated from the last execution context
        return {
            "explanation": "Rule execution completed",
            "suggestion": "Use the trace field from ExecutionResult for detailed execution information"
        }


# Convenience function
def from_yaml(yaml_content: str) -> Engine:
    """Create engine from YAML - convenience function for AI agents."""
    return Engine.from_yaml(yaml_content) 