"""
Symbolica Rule Engine
=====================

Simple, deterministic rule engine for AI agent decision-making.
Focused on clear LLM explainability without overengineering.
"""

import time
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from .models import Rule, Facts, ExecutionContext, ExecutionResult, Goal, facts
from .exceptions import ValidationError
from .._internal.evaluator import ASTEvaluator
from .._internal.dag import DAGStrategy
from .._internal.backward_chainer import BackwardChainer


class Engine:
    """Simple rule engine for AI agents."""
    
    def __init__(self, rules: Optional[List[Rule]] = None):
        """Initialize engine with rules."""
        self._rules = rules or []
        self._evaluator = ASTEvaluator()
        self._dag_strategy = DAGStrategy(self._evaluator)
        self._backward_chainer = BackwardChainer(self._rules, self._evaluator)
        
        if self._rules:
            self._validate_rules()
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> 'Engine':
        """Create engine from YAML string."""
        rules = cls._parse_yaml_rules(yaml_content)
        return cls(rules)
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> 'Engine':
        """Create engine from YAML file."""
        try:
            with open(file_path, 'r') as f:
                yaml_content = f.read()
            return cls.from_yaml(yaml_content)
        except FileNotFoundError:
            raise ValidationError(f"File not found: {file_path}")
    
    @classmethod
    def from_directory(cls, directory_path: Union[str, Path]) -> 'Engine':
        """Create engine from directory containing YAML files."""
        all_rules = []
        for yaml_file in Path(directory_path).rglob("*.yaml"):
            with open(yaml_file, 'r') as f:
                file_rules = cls._parse_yaml_rules(f.read())
                all_rules.extend(file_rules)
        
        if not all_rules:
            raise ValidationError(f"No rules found in {directory_path}")
        
        return cls(all_rules)
    
    def reason(self, input_facts: Union[Facts, Dict[str, Any]]) -> ExecutionResult:
        """Execute rules against facts and return result with simple explanation."""
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
        
        # Execute rules in dependency-aware order (includes chaining)
        execution_order = self._dag_strategy.get_execution_order(self._rules)
        triggered_rules = set()  # Track which rules were triggered
        
        for rule in execution_order:
            # Check if this rule was triggered by another rule
            triggered_by = self._find_triggering_rule(rule, context.fired_rules)
            if triggered_by:
                triggered_rules.add(rule.id)
            
            self._execute_rule(rule, context, triggered_by)
        
        # Build result
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            verdict=context.verdict,
            fired_rules=context.fired_rules,
            execution_time_ms=execution_time_ms,
            reasoning=context.reasoning
        )
    
    def _execute_rule(self, rule: Rule, context: ExecutionContext, triggered_by: Optional[str] = None) -> None:
        """Execute a single rule."""
        try:
            # Evaluate with trace to get detailed explanation
            trace = self._evaluator.evaluate_with_trace(rule.condition, context)
            
            if trace.result:
                # Apply actions
                for key, value in rule.actions.items():
                    context.set_fact(key, value)
                
                # Record detailed reasoning using trace
                detailed_reason = trace.explain()
                actions_str = ", ".join([f"{k}={v}" for k, v in rule.actions.items()])
                reason = f"{detailed_reason}, set {actions_str}"
                context.rule_fired(rule.id, reason, triggered_by)
        except Exception:
            # Skip rule if evaluation fails
            pass
    
    def _find_triggering_rule(self, rule: Rule, fired_rules: List[str]) -> Optional[str]:
        """Find which rule triggered this rule, if any."""
        for fired_rule_id in fired_rules:
            fired_rule = next((r for r in self._rules if r.id == fired_rule_id), None)
            if fired_rule and rule.id in fired_rule.triggers:
                return fired_rule_id
        return None
    
    def find_rules_for_goal(self, goal: Goal) -> List[Rule]:
        """Find rules that can produce the goal (reverse DAG search)."""
        return self._backward_chainer.find_supporting_rules(goal)
    
    def can_achieve_goal(self, goal: Goal, current_facts: Union[Facts, Dict[str, Any]]) -> bool:
        """Test if goal can be achieved with current facts."""
        if isinstance(current_facts, dict):
            current_facts = Facts(current_facts)
        
        return self._backward_chainer.can_achieve_goal(goal, current_facts)
    

    
    def _validate_rules(self) -> None:
        """Basic rule validation including chaining validation."""
        rule_ids = [rule.id for rule in self._rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValidationError("Duplicate rule IDs found")
        
        # Validate rule chaining
        self._validate_rule_chaining()
    
    def _validate_rule_chaining(self) -> None:
        """Validate rule chaining to prevent circular dependencies."""
        rule_ids = {rule.id for rule in self._rules}
        
        # Check that all triggered rules exist
        for rule in self._rules:
            for triggered_id in rule.triggers:
                if triggered_id not in rule_ids:
                    raise ValidationError(f"Rule '{rule.id}' triggers unknown rule '{triggered_id}'")
        
        # Check for circular dependencies using DFS
        def has_cycle(start_rule_id: str, visited: set, path: set) -> bool:
            if start_rule_id in path:
                return True
            if start_rule_id in visited:
                return False
            
            visited.add(start_rule_id)
            path.add(start_rule_id)
            
            # Find the rule with this ID
            rule = next((r for r in self._rules if r.id == start_rule_id), None)
            if rule:
                for triggered_id in rule.triggers:
                    if has_cycle(triggered_id, visited, path):
                        return True
            
            path.remove(start_rule_id)
            return False
        
        visited = set()
        for rule in self._rules:
            if rule.id not in visited:
                if has_cycle(rule.id, visited, set()):
                    raise ValidationError(f"Circular dependency detected in rule chaining involving rule '{rule.id}'")
    
    @staticmethod
    def _parse_yaml_rules(yaml_content: str) -> List[Rule]:
        """Parse YAML content into rules."""
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML: {e}")
        
        if not data or 'rules' not in data:
            raise ValidationError("YAML must contain 'rules' key")
        
        rules = []
        for rule_dict in data['rules']:
            # Handle structured conditions by converting to string
            condition = rule_dict.get('condition') or rule_dict.get('if')
            if isinstance(condition, dict):
                condition = Engine._convert_condition(condition)
            
            actions = rule_dict.get('actions') or rule_dict.get('then', {})
            
            rule = Rule(
                id=rule_dict['id'],
                priority=rule_dict.get('priority', 0),
                condition=condition,
                actions=actions,
                tags=rule_dict.get('tags', []),
                triggers=rule_dict.get('triggers', [])
            )
            rules.append(rule)
        
        return rules
    
    @staticmethod
    def _convert_condition(condition_dict: Dict[str, Any]) -> str:
        """Convert structured condition to simple string."""
        if 'all' in condition_dict:
            conditions = [f"({c})" for c in condition_dict['all']]
            return " and ".join(conditions)
        elif 'any' in condition_dict:
            conditions = [f"({c})" for c in condition_dict['any']]
            return " or ".join(conditions)
        elif 'not' in condition_dict:
            return f"not ({condition_dict['not']})"
        else:
            return str(condition_dict)
    
    @property
    def rules(self) -> List[Rule]:
        """Get all rules."""
        return self._rules.copy()
    
    @property
    def rule_count(self) -> int:
        """Get rule count."""
        return len(self._rules)
    
    # Simple methods for test compatibility
    def get_analysis(self) -> Dict[str, Any]:
        """Get basic rule analysis."""
        return {
            'rule_count': len(self._rules),
            'rule_ids': [rule.id for rule in self._rules],
            'avg_priority': sum(rule.priority for rule in self._rules) / len(self._rules) if self._rules else 0
        }
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get rule by ID."""
        return next((rule for rule in self._rules if rule.id == rule_id), None) 