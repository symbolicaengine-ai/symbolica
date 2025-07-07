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

from .models import Rule, Facts, ExecutionContext, ExecutionResult, facts
from .exceptions import ValidationError
from .._internal.evaluator import create_evaluator
from .._internal.executor import SimpleActionExecutor
from .._internal.dag import DAGStrategy


class Engine:
    """Simple rule engine for AI agents."""
    
    def __init__(self, rules: Optional[List[Rule]] = None):
        """Initialize engine with rules."""
        self._rules = rules or []
        self._evaluator = create_evaluator()
        self._executor = SimpleActionExecutor()
        self._dag_strategy = DAGStrategy()
        
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
        
        # Execute rules in priority order
        execution_order = self._dag_strategy.get_execution_order(self._rules)
        for rule in execution_order:
            self._execute_rule(rule, context)
        
        # Build result
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            verdict=context.verdict,
            fired_rules=context.fired_rules,
            execution_time_ms=execution_time_ms,
            reasoning=context.reasoning
        )
    
    def _execute_rule(self, rule: Rule, context: ExecutionContext) -> None:
        """Execute a single rule."""
        try:
            if self._evaluator.evaluate(rule.condition, context):
                # Apply actions
                for key, value in rule.actions.items():
                    context.set_fact(key, value)
                
                # Record detailed reasoning
                detailed_reason = self._explain_condition(rule.condition, context)
                actions_str = ", ".join([f"{k}={v}" for k, v in rule.actions.items()])
                reason = f"{detailed_reason}, set {actions_str}"
                context.rule_fired(rule.id, reason)
        except Exception:
            # Skip rule if evaluation fails
            pass
    
    def _explain_condition(self, condition: str, context: ExecutionContext) -> str:
        """Explain why a condition was true with actual values."""
        try:
            # Handle OR conditions - find which part made it true
            if ' or ' in condition:
                parts = [part.strip() for part in condition.split(' or ')]
                true_parts = []
                for part in parts:
                    try:
                        if self._evaluator.evaluate(part, context):
                            explained = self._explain_simple_condition(part, context)
                            true_parts.append(explained)
                    except:
                        pass
                
                if true_parts:
                    return f"Condition true because: {' OR '.join(true_parts)}"
            
            # Handle AND conditions - show all parts
            elif ' and ' in condition:
                parts = [part.strip() for part in condition.split(' and ')]
                explained_parts = []
                for part in parts:
                    try:
                        explained = self._explain_simple_condition(part, context)
                        explained_parts.append(explained)
                    except:
                        explained_parts.append(f"({part})")
                
                return f"Condition true: {' AND '.join(explained_parts)}"
            
            # Simple condition
            else:
                return self._explain_simple_condition(condition, context)
                
        except Exception:
            return f"Condition '{condition}' was true"
    
    def _explain_simple_condition(self, condition: str, context: ExecutionContext) -> str:
        """Explain a simple condition with actual values."""
        try:
            condition = condition.strip('()')
            
            # Common comparison operators
            for op in ['>=', '<=', '==', '!=', '>', '<']:
                if op in condition:
                    left, right = condition.split(op, 1)
                    left, right = left.strip(), right.strip()
                    
                    # Get actual value
                    try:
                        left_val = self._get_field_value(left, context)
                        right_val = self._get_field_value(right, context)
                        return f"{left}({left_val}) {op} {right_val}"
                    except:
                        return f"({condition})"
            
            # Handle 'in' operator
            if ' in ' in condition:
                left, right = condition.split(' in ', 1)
                left, right = left.strip(), right.strip()
                try:
                    left_val = self._get_field_value(left, context)
                    return f"{left}({left_val}) in {right}"
                except:
                    return f"({condition})"
            
            # Handle 'not' operator
            if condition.startswith('not '):
                sub_condition = condition[4:].strip()
                return f"NOT({self._explain_simple_condition(sub_condition, context)})"
            
            return f"({condition})"
            
        except Exception:
            return f"({condition})"
    
    def _get_field_value(self, field: str, context: ExecutionContext) -> Any:
        """Get the actual value of a field from context."""
        # Remove quotes if it's a string literal
        if (field.startswith('"') and field.endswith('"')) or (field.startswith("'") and field.endswith("'")):
            return field
        
        # Try to parse as number
        try:
            if '.' in field:
                return float(field)
            return int(field)
        except ValueError:
            pass
        
        # Get from context
        return context.get_fact(field, field)
    
    def _validate_rules(self) -> None:
        """Basic rule validation."""
        rule_ids = [rule.id for rule in self._rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValidationError("Duplicate rule IDs found")
    
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
                tags=rule_dict.get('tags', [])
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