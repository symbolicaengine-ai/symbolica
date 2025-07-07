"""
Symbolica Rule Engine
=====================

Simple, deterministic rule engine for AI agent decision-making.
Focused on clear LLM explainability without overengineering.
"""

import os
import time
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from .models import Rule, Facts, ExecutionContext, ExecutionResult, facts
from .exceptions import ValidationError, EvaluationError
from .._internal.evaluator import create_evaluator
from .._internal.executor import SimpleActionExecutor
from .._internal.dag import DAGStrategy


class Engine:
    """
    Simple rule engine with clear explanations for LLM integration.
    
    Features:
    - YAML rule loading (string, file, directory)
    - Deterministic execution with dependency resolution
    - Simple explanations for AI agents
    """
    
    def __init__(self, rules: List[Rule]):
        """Initialize engine with rules."""
        self._rules = rules
        self._evaluator = create_evaluator()
        self._executor = SimpleActionExecutor()
        self._dag_strategy = DAGStrategy()
        
        # Validate rules
        self._validate_rules()
        
        # Build dependency graph
        self._dependency_graph = self._build_dependency_graph()
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> 'Engine':
        """Create engine from YAML string."""
        rules = cls._parse_yaml_rules(yaml_content)
        return cls(rules)
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> 'Engine':
        """Create engine from YAML file."""
        with open(file_path, 'r') as f:
            yaml_content = f.read()
        return cls.from_yaml(yaml_content)
    
    @classmethod
    def from_directory(cls, directory_path: Union[str, Path]) -> 'Engine':
        """Create engine from directory containing YAML files."""
        all_rules = []
        
        for yaml_file in Path(directory_path).rglob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    yaml_content = f.read()
                file_rules = cls._parse_yaml_rules(yaml_content)
                all_rules.extend(file_rules)
            except Exception as e:
                raise ValidationError(f"Failed to load {yaml_file}: {e}")
        
        if not all_rules:
            raise ValidationError(f"No valid rules found in {directory_path}")
        
        return cls(all_rules)
    
    def reason(self, input_facts: Union[Facts, Dict[str, Any]]) -> ExecutionResult:
        """
        Execute rules against facts and return result with simple explanation.
        
        Args:
            input_facts: Facts object or dictionary of input facts
        """
        start_time = time.perf_counter()
        
        # Convert dictionary to Facts if needed
        if isinstance(input_facts, dict):
            input_facts = Facts(input_facts)
        
        # Create execution context
        context = ExecutionContext(
            original_facts=input_facts,
            enriched_facts={},
            fired_rules=[]
        )
        
        # Get execution order using DAG strategy
        execution_order = self._dag_strategy.get_execution_order(self._rules)
        
        # Execute rules in dependency order
        for rule in execution_order:
            self._execute_rule(rule, context)
        
        # Calculate execution time
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Build simple result
        result = ExecutionResult(
            verdict=context.verdict,
            fired_rules=context.fired_rules,
            execution_time_ms=execution_time_ms,
            reasoning=context.reasoning
        )
        
        return result
    
    def _execute_rule(self, rule: Rule, context: ExecutionContext) -> None:
        """Execute a single rule with simple explanation."""
        try:
            # Evaluate condition
            condition_fired = self._evaluator.evaluate(rule.condition, context)
            
            if condition_fired:
                # Apply actions
                for key, value in rule.actions.items():
                    context.set_fact(key, value)
                
                # Record simple reasoning
                actions_str = ", ".join([f"{k}={v}" for k, v in rule.actions.items()])
                reason = f"Condition '{rule.condition}' was true, set {actions_str}"
                context.rule_fired(rule.id, reason)
                
        except Exception as e:
            # Skip rule if evaluation fails
            pass
    
    def _validate_rules(self) -> None:
        """Validate rules for consistency."""
        if not self._rules:
            raise ValidationError("No rules provided")
        
        # Check for duplicate rule IDs
        rule_ids = [rule.id for rule in self._rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValidationError("Duplicate rule IDs found")
        
        # Validate each rule's condition can be parsed
        for rule in self._rules:
            try:
                self._evaluator.extract_fields(rule.condition)
            except Exception as e:
                raise ValidationError(f"Invalid condition in rule {rule.id}: {e}")
    
    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """Build dependency graph from rules."""
        graph = {}
        
        for rule in self._rules:
            # Extract fields this rule depends on
            depends_on = self._evaluator.extract_fields(rule.condition)
            
            # Extract fields this rule sets
            sets_fields = set(rule.actions.keys())
            
            # Build dependencies
            dependencies = []
            for other_rule in self._rules:
                if other_rule.id == rule.id:
                    continue
                
                # Check if other rule sets fields this rule depends on
                other_sets = set(other_rule.actions.keys())
                if depends_on & other_sets:
                    dependencies.append(other_rule.id)
            
            graph[rule.id] = dependencies
        
        return graph
    
    @staticmethod
    def _parse_yaml_rules(yaml_content: str) -> List[Rule]:
        """Parse YAML content into rules."""
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML: {e}")
        
        if not isinstance(data, dict):
            raise ValidationError("YAML must contain a dictionary")
        
        rules = []
        
        # Handle different YAML structures
        if 'rules' in data:
            rule_data = data['rules']
        elif 'ruleset' in data:
            rule_data = data['ruleset']
        else:
            # Assume entire document is rules
            rule_data = data
        
        if not isinstance(rule_data, list):
            raise ValidationError("Rules must be a list")
        
        for idx, rule_dict in enumerate(rule_data):
            if not isinstance(rule_dict, dict):
                raise ValidationError(f"Rule {idx} must be a dictionary")
            
            # Extract rule components with flexible naming
            rule_id = rule_dict.get('id', f"rule_{idx}")
            priority = rule_dict.get('priority', 0)
            
            # Support both 'condition' and 'if' keys
            condition = rule_dict.get('condition') or rule_dict.get('if')
            if not condition:
                raise ValidationError(f"Rule {rule_id} missing condition")
            
            # Support both 'actions' and 'then' keys
            actions = rule_dict.get('actions') or rule_dict.get('then', {})
            if not actions:
                raise ValidationError(f"Rule {rule_id} missing actions")
            
            # Extract tags
            tags = rule_dict.get('tags', [])
            if isinstance(tags, str):
                tags = [tags]
            
            # Create rule
            rule = Rule(
                id=rule_id,
                priority=priority,
                condition=condition,
                actions=actions,
                tags=tags
            )
            rules.append(rule)
        
        return rules
    
    @property
    def rules(self) -> List[Rule]:
        """Get all rules."""
        return self._rules.copy()
    
    @property
    def rule_count(self) -> int:
        """Get total number of rules."""
        return len(self._rules) 