"""
YAML Rule Parser
===============

Comprehensive parser for YAML rule files supporting multiple formats:
- Single rule format (rule: {...})
- Multi-rule format (rules: [...])
- Flexible expression parsing
- Comprehensive validation
"""

import yaml
import pathlib
from typing import List, Dict, Any, Union, Optional
from dataclasses import dataclass

from ..core import (
    Rule, RuleId, Priority, Condition, Action, Facts,
    rule_id, priority, condition, action_set, action_call,
    ValidationError
)


@dataclass
class RuleParseResult:
    """Result of parsing rules with metadata."""
    rules: List[Rule]
    errors: List[str]
    warnings: List[str]
    source_file: Optional[str] = None


class RuleParser:
    """
    Comprehensive YAML rule parser.
    
    Supports multiple rule formats and expression types.
    """
    
    def __init__(self, strict: bool = False):
        self.strict = strict
    
    def parse_file(self, file_path: Union[str, pathlib.Path]) -> RuleParseResult:
        """Parse rules from YAML file."""
        path = pathlib.Path(file_path)
        
        if not path.exists():
            return RuleParseResult(
                rules=[],
                errors=[f"File not found: {file_path}"],
                warnings=[],
                source_file=str(file_path)
            )
        
        try:
            content = path.read_text(encoding='utf-8')
            result = self.parse_string(content)
            result.source_file = str(file_path)
            return result
        except Exception as e:
            return RuleParseResult(
                rules=[],
                errors=[f"Failed to read file {file_path}: {e}"],
                warnings=[],
                source_file=str(file_path)
            )
    
    def parse_string(self, yaml_content: str) -> RuleParseResult:
        """Parse rules from YAML string."""
        errors = []
        warnings = []
        rules = []
        
        try:
            # Parse YAML
            data = yaml.safe_load(yaml_content)
            
            if not data:
                return RuleParseResult(
                    rules=[],
                    errors=["Empty YAML content"],
                    warnings=[]
                )
            
            # Handle different formats
            if 'rules' in data:
                # Multi-rule format
                rules, parse_errors, parse_warnings = self._parse_multi_rule_format(data)
            elif 'rule' in data:
                # Single rule format
                rules, parse_errors, parse_warnings = self._parse_single_rule_format(data)
            else:
                errors.append("YAML must contain either 'rule' or 'rules' key")
            
            errors.extend(parse_errors)
            warnings.extend(parse_warnings)
            
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML syntax: {e}")
        except Exception as e:
            errors.append(f"Unexpected error parsing YAML: {e}")
        
        return RuleParseResult(
            rules=rules,
            errors=errors,
            warnings=warnings
        )
    
    def _parse_multi_rule_format(self, data: Dict[str, Any]) -> tuple[List[Rule], List[str], List[str]]:
        """Parse multi-rule format: rules: [...]"""
        rules = []
        errors = []
        warnings = []
        
        rules_data = data.get('rules', [])
        
        if not isinstance(rules_data, list):
            errors.append("'rules' must be a list")
            return [], errors, warnings
        
        for i, rule_data in enumerate(rules_data):
            try:
                rule = self._parse_single_rule(rule_data, context=f"rule[{i}]")
                rules.append(rule)
            except Exception as e:
                errors.append(f"Error parsing rule[{i}]: {e}")
                if self.strict:
                    break
        
        return rules, errors, warnings
    
    def _parse_single_rule_format(self, data: Dict[str, Any]) -> tuple[List[Rule], List[str], List[str]]:
        """Parse single rule format: rule: {...}"""
        rules = []
        errors = []
        warnings = []
        
        rule_data = data.get('rule', {})
        
        try:
            rule = self._parse_single_rule(rule_data, context="rule")
            rules.append(rule)
        except Exception as e:
            errors.append(f"Error parsing rule: {e}")
        
        return rules, errors, warnings
    
    def _parse_single_rule(self, rule_data: Dict[str, Any], context: str = "rule") -> Rule:
        """Parse a single rule dictionary."""
        # Validate required fields
        if 'id' not in rule_data:
            raise ValidationError(f"{context} missing required 'id' field")
        
        if 'if' not in rule_data and 'condition' not in rule_data:
            raise ValidationError(f"{context} missing required 'if' or 'condition' field")
        
        if 'then' not in rule_data and 'actions' not in rule_data:
            raise ValidationError(f"{context} missing required 'then' or 'actions' field")
        
        # Parse rule ID
        rule_id_obj = rule_id(str(rule_data['id']))
        
        # Parse priority
        priority_obj = priority(int(rule_data.get('priority', 50)))
        
        # Parse condition
        condition_expr = rule_data.get('if', rule_data.get('condition', ''))
        condition_obj = condition(self._normalize_condition(condition_expr))
        
        # Parse actions
        actions = self._parse_actions(rule_data.get('then', rule_data.get('actions', {})))
        
        # Parse tags
        tags = frozenset(rule_data.get('tags', []))
        
        return Rule(
            id=rule_id_obj,
            priority=priority_obj,
            condition=condition_obj,
            actions=actions,
            tags=tags
        )
    
    def _normalize_condition(self, condition_expr: Any) -> str:
        """Normalize condition to string format for processing."""
        if isinstance(condition_expr, str):
            return condition_expr.strip()
        elif isinstance(condition_expr, dict):
            # Keep structured format as-is for the evaluator
            return str(condition_expr)
        elif isinstance(condition_expr, list):
            # Convert list to structured format
            return str({'all': condition_expr})
        else:
            return str(condition_expr)
    
    def _parse_actions(self, actions_data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List[Action]:
        """Parse actions from various formats."""
        if isinstance(actions_data, dict):
            return self._parse_actions_dict(actions_data)
        elif isinstance(actions_data, list):
            return self._parse_actions_list(actions_data)
        else:
            raise ValidationError(f"Actions must be dict or list, got {type(actions_data)}")
    
    def _parse_actions_dict(self, actions_data: Dict[str, Any]) -> List[Action]:
        """Parse actions from dictionary format."""
        actions = []
        
        # Handle 'set' action
        if 'set' in actions_data:
            set_data = actions_data['set']
            if isinstance(set_data, dict):
                actions.append(action_set(**set_data))
            else:
                raise ValidationError(f"'set' action must be a dictionary, got {type(set_data)}")
        
        # Handle 'call' action
        if 'call' in actions_data:
            call_data = actions_data['call']
            if isinstance(call_data, dict):
                function_name = call_data.get('function', '')
                params = call_data.get('params', {})
                actions.append(action_call(function_name, **params))
            else:
                raise ValidationError(f"'call' action must be a dictionary, got {type(call_data)}")
        
        # Handle other action types
        for action_type, action_params in actions_data.items():
            if action_type not in ['set', 'call']:
                actions.append(Action(action_type, action_params))
        
        if not actions:
            raise ValidationError("No valid actions found")
        
        return actions
    
    def _parse_actions_list(self, actions_data: List[Dict[str, Any]]) -> List[Action]:
        """Parse actions from list format."""
        actions = []
        
        for action_data in actions_data:
            if not isinstance(action_data, dict):
                raise ValidationError(f"Action must be a dictionary, got {type(action_data)}")
            
            if len(action_data) != 1:
                raise ValidationError(f"Action must have exactly one key, got {list(action_data.keys())}")
            
            action_type, action_params = next(iter(action_data.items()))
            
            if action_type == 'set':
                if isinstance(action_params, dict):
                    actions.append(action_set(**action_params))
                else:
                    raise ValidationError(f"'set' action parameters must be dict, got {type(action_params)}")
            elif action_type == 'call':
                if isinstance(action_params, dict):
                    function_name = action_params.get('function', '')
                    params = action_params.get('params', {})
                    actions.append(action_call(function_name, **params))
                else:
                    raise ValidationError(f"'call' action parameters must be dict, got {type(action_params)}")
            else:
                actions.append(Action(action_type, action_params))
        
        return actions


# Convenience functions
def parse_yaml_file(file_path: Union[str, pathlib.Path], strict: bool = False) -> RuleParseResult:
    """Parse rules from YAML file."""
    parser = RuleParser(strict=strict)
    return parser.parse_file(file_path)


def parse_yaml_string(yaml_content: str, strict: bool = False) -> RuleParseResult:
    """Parse rules from YAML string."""
    parser = RuleParser(strict=strict)
    return parser.parse_string(yaml_content)


def parse_yaml_directory(directory: Union[str, pathlib.Path], strict: bool = False) -> RuleParseResult:
    """Parse all YAML files in a directory."""
    dir_path = pathlib.Path(directory)
    
    if not dir_path.exists():
        return RuleParseResult(
            rules=[],
            errors=[f"Directory not found: {directory}"],
            warnings=[]
        )
    
    all_rules = []
    all_errors = []
    all_warnings = []
    
    # Find all YAML files
    yaml_files = list(dir_path.rglob('*.yaml')) + list(dir_path.rglob('*.yml'))
    
    if not yaml_files:
        return RuleParseResult(
            rules=[],
            errors=[f"No YAML files found in directory: {directory}"],
            warnings=[]
        )
    
    parser = RuleParser(strict=strict)
    
    for yaml_file in yaml_files:
        # Skip registry files
        if yaml_file.name.endswith('.reg.yaml') or yaml_file.name.endswith('.reg.yml'):
            continue
        
        result = parser.parse_file(yaml_file)
        all_rules.extend(result.rules)
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)
        
        if strict and result.errors:
            break
    
    return RuleParseResult(
        rules=all_rules,
        errors=all_errors,
        warnings=all_warnings
    ) 