"""
Symbolica Rule Engine
=====================

Deterministic rule engine for AI agent decision-making.
Provides comprehensive tracing and explainable reasoning.
"""

import os
import time
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from .models import (
    Rule, Facts, ExecutionContext, ExecutionResult, 
    RuleEvaluationTrace, ConditionTrace, FieldAccess,
    TraceLevel, facts
)
from .exceptions import ValidationError, EvaluationError
from .._internal.evaluator import create_evaluator
from .._internal.executor import SimpleActionExecutor
from .._internal.dag import DAGStrategy


class Engine:
    """
    Main rule engine with comprehensive tracing and explainable reasoning.
    
    Features:
    - YAML rule loading (string, file, directory)
    - Deterministic execution with dependency resolution
    - Detailed tracing for AI explainability
    - LLM-friendly reasoning explanations
    """
    
    def __init__(self, rules: List[Rule], trace_level: TraceLevel = TraceLevel.DETAILED):
        """Initialize engine with rules and trace level."""
        self._rules = rules
        self._trace_level = trace_level
        self._evaluator = create_evaluator()
        self._executor = SimpleActionExecutor()
        self._dag_strategy = DAGStrategy()
        
        # Validate rules
        self._validate_rules()
        
        # Build dependency graph
        self._dependency_graph = self._build_dependency_graph()
    
    @classmethod
    def from_yaml(cls, yaml_content: str, trace_level: TraceLevel = TraceLevel.DETAILED) -> 'Engine':
        """Create engine from YAML string."""
        rules = cls._parse_yaml_rules(yaml_content)
        return cls(rules, trace_level)
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path], trace_level: TraceLevel = TraceLevel.DETAILED) -> 'Engine':
        """Create engine from YAML file."""
        with open(file_path, 'r') as f:
            yaml_content = f.read()
        return cls.from_yaml(yaml_content, trace_level)
    
    @classmethod
    def from_directory(cls, directory_path: Union[str, Path], trace_level: TraceLevel = TraceLevel.DETAILED) -> 'Engine':
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
        
        return cls(all_rules, trace_level)
    
    def reason(self, input_facts: Union[Facts, Dict[str, Any]]) -> ExecutionResult:
        """
        Execute rules against facts and return comprehensive result with detailed tracing.
        
        This is the core method that provides deterministic, traceable reasoning
        for AI agents. The result includes detailed explanations of why each
        rule fired or didn't fire, suitable for LLM prompt inclusion.
        
        Args:
            input_facts: Facts object or dictionary of input facts
        """
        start_time = time.perf_counter()
        
        # Convert dictionary to Facts if needed
        if isinstance(input_facts, dict):
            input_facts = Facts(input_facts)
        
        # Create execution context with enhanced tracing
        context = ExecutionContext(
            original_facts=input_facts,
            enriched_facts={},
            fired_rules=[],
            trace_level=self._trace_level
        )
        
        # Get execution order using DAG strategy
        execution_order = self._dag_strategy.get_execution_order(self._rules)
        
        # Execute rules in dependency order with detailed tracing
        for rule in execution_order:
            self._execute_rule_with_trace(rule, context)
        
        # Calculate execution time
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Build comprehensive result
        result = ExecutionResult(
            verdict=context.verdict,
            fired_rules=context.fired_rules,
            execution_time_ms=execution_time_ms,
            trace=self._build_simple_trace(context),
            rule_traces=context.rule_traces
        )
        
        return result
    
    def _execute_rule_with_trace(self, rule: Rule, context: ExecutionContext) -> None:
        """Execute a single rule with comprehensive tracing."""
        rule_start_time = time.perf_counter_ns()
        
        # Mark rule evaluation start for tracing
        context.start_rule_evaluation(rule.id)
        
        # Track field accesses before condition evaluation
        field_accesses_before = len(context.field_accesses)
        
        # Evaluate condition with detailed trace
        condition_fired, condition_trace = self._evaluator.evaluate_with_trace(
            rule.condition, context
        )
        
        # Extract field accesses from this rule's evaluation
        rule_field_accesses = context.field_accesses[field_accesses_before:]
        
        # Initialize trace data
        actions_applied = {}
        field_changes = []
        
        # Execute actions if condition fired
        if condition_fired:
            actions_applied = rule.actions.copy()
            
            # Apply actions and track field changes
            for key, value in rule.actions.items():
                old_value = context.enriched_facts.get(key)
                context.set_fact(key, value)
                
                # Find the field access record for this change
                for fa in reversed(context.field_accesses):
                    if fa.field_name == key and fa.access_type == 'write' and fa.rule_id == rule.id:
                        field_changes.append(fa)
                        break
            
            # Record rule as fired
            context.rule_fired(rule.id)
        
        # Calculate rule execution time
        rule_execution_time = time.perf_counter_ns() - rule_start_time
        
        # Create comprehensive rule trace
        rule_trace = RuleEvaluationTrace(
            rule_id=rule.id,
            priority=rule.priority,
            condition_trace=condition_trace,
            fired=condition_fired,
            actions_applied=actions_applied,
            field_changes=field_changes,
            execution_time_ns=rule_execution_time,
            tags=rule.tags
        )
        
        # Add trace to context
        context.add_rule_trace(rule_trace)
    
    def _build_simple_trace(self, context: ExecutionContext) -> Dict[str, Any]:
        """Build simple trace for backward compatibility."""
        return {
            'execution_order': [rt.rule_id for rt in context.rule_traces],
            'fired_rules': context.fired_rules,
            'total_rules': len(context.rule_traces),
            'field_accesses': len(context.field_accesses),
            'context_id': context.context_id
        }
    
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
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get rule by ID."""
        for rule in self._rules:
            if rule.id == rule_id:
                return rule
        return None
    
    def explain_rule(self, rule_id: str) -> Dict[str, Any]:
        """Get explanation of a specific rule."""
        rule = self.get_rule(rule_id)
        if not rule:
            return {"error": f"Rule {rule_id} not found"}
        
        # Extract fields used by this rule
        condition_fields = self._evaluator.extract_fields(rule.condition)
        action_fields = set(rule.actions.keys())
        
        return {
            "rule_id": rule.id,
            "priority": rule.priority,
            "condition": rule.condition,
            "actions": rule.actions,
            "tags": rule.tags,
            "dependencies": {
                "reads_fields": list(condition_fields),
                "writes_fields": list(action_fields)
            }
        } 