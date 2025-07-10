"""
Rule Loading and Parsing
========================

Handles loading and parsing of rules from various sources.
Separated from Engine to follow Single Responsibility Principle.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Union

from ..models import Rule
from .exceptions import ValidationError


class ConditionParser:
    """Handles conversion of structured conditions to evaluatable strings."""
    
    @staticmethod
    def convert_condition(condition_dict: Dict[str, Any]) -> str:
        """Convert structured condition to evaluatable string expression."""
        def _process_condition_node(node: Any) -> str:
            """Recursively process condition nodes."""
            if isinstance(node, str):
                # Base case: string condition
                return node.strip()
            
            elif isinstance(node, dict):
                # Structured condition node
                if not node:
                    raise ValidationError("Empty condition dictionary")
                
                # Handle multiple keys at same level (combine with AND)
                subconditions = []
                for key, value in node.items():
                    
                    if key == 'all':
                        if not isinstance(value, list) or not value:
                            raise ValidationError("'all' must contain a non-empty list of conditions")
                        conditions = [f"({_process_condition_node(item)})" for item in value]
                        subconditions.append(" and ".join(conditions))
                    
                    elif key == 'any':
                        if not isinstance(value, list) or not value:
                            raise ValidationError("'any' must contain a non-empty list of conditions")
                        conditions = [f"({_process_condition_node(item)})" for item in value]
                        subconditions.append(f"({' or '.join(conditions)})")
                    
                    elif key == 'not':
                        if value is None or value == "":
                            raise ValidationError("'not' must contain a valid condition")
                        subconditions.append(f"not ({_process_condition_node(value)})")
                    
                    else:
                        raise ValidationError(f"Unknown structured condition key: '{key}'. Valid keys are: all, any, not")
                
                # Combine all subconditions with AND
                if len(subconditions) == 1:
                    return subconditions[0]
                else:
                    return " and ".join([f"({cond})" for cond in subconditions])
            
            elif isinstance(node, list):
                raise ValidationError("Lists must be contained within 'all' or 'any' structures")
            
            else:
                raise ValidationError(f"Invalid condition node type: {type(node)}. Must be string or dict")
        
        return _process_condition_node(condition_dict)


class RuleLoader:
    """Handles loading and parsing rules from various sources."""
    
    def __init__(self):
        self.condition_parser = ConditionParser()
    
    def from_yaml(self, yaml_content: str) -> List[Rule]:
        """Create rules from YAML string."""
        return self._parse_yaml_rules(yaml_content)
    
    def from_file(self, file_path: Union[str, Path]) -> List[Rule]:
        """Create rules from YAML file."""
        try:
            with open(file_path, 'r') as f:
                yaml_content = f.read()
            return self.from_yaml(yaml_content)
        except FileNotFoundError:
            raise ValidationError(f"File not found: {file_path}")
        except Exception as e:
            raise ValidationError(f"Error reading file {file_path}: {e}")
    
    def from_directory(self, directory_path: Union[str, Path]) -> List[Rule]:
        """Create rules from directory containing YAML files."""
        all_rules = []
        directory = Path(directory_path)
        
        if not directory.exists():
            raise ValidationError(f"Directory not found: {directory_path}")
        
        yaml_files = list(directory.rglob("*.yaml")) + list(directory.rglob("*.yml"))
        
        if not yaml_files:
            raise ValidationError(f"No YAML files found in {directory_path}")
        
        for yaml_file in yaml_files:
            try:
                file_rules = self.from_file(yaml_file)
                all_rules.extend(file_rules)
            except Exception as e:
                raise ValidationError(f"Error loading {yaml_file}: {e}")
        
        if not all_rules:
            raise ValidationError(f"No rules found in {directory_path}")
        
        return all_rules
    
    def _parse_yaml_rules(self, yaml_content: str) -> List[Rule]:
        """Parse YAML content into rules."""
        if not yaml_content or not yaml_content.strip():
            raise ValidationError("YAML content cannot be empty")
        
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML: {e}")
        
        if not data:
            raise ValidationError("YAML content is empty or invalid")
        
        if not isinstance(data, dict):
            raise ValidationError("YAML must contain a dictionary")
        
        if 'rules' not in data:
            raise ValidationError("YAML must contain 'rules' key")
        
        if not isinstance(data['rules'], list):
            raise ValidationError("'rules' must be a list")
        
        if not data['rules']:
            raise ValidationError("Rules list cannot be empty")
        
        rules = []
        for i, rule_dict in enumerate(data['rules']):
            try:
                rule = self._parse_single_rule(rule_dict)
                rules.append(rule)
            except Exception as e:
                raise ValidationError(f"Error parsing rule at index {i}: {e}")
        
        return rules
    
    def _parse_single_rule(self, rule_dict: Dict[str, Any]) -> Rule:
        """Parse a single rule dictionary into a Rule object."""
        if not isinstance(rule_dict, dict):
            raise ValidationError("Rule must be a dictionary")
        
        # Validate required fields
        if 'id' not in rule_dict:
            raise ValidationError("Rule must have 'id' field")
        
        if not rule_dict.get('condition') and not rule_dict.get('if'):
            raise ValidationError("Rule must have 'condition' or 'if' field")
        
        if not rule_dict.get('actions') and not rule_dict.get('then'):
            raise ValidationError("Rule must have 'actions' or 'then' field")
        
        # Extract and process condition
        condition = rule_dict.get('condition') or rule_dict.get('if')
        if isinstance(condition, dict):
            condition = self.condition_parser.convert_condition(condition)
        elif not isinstance(condition, str):
            raise ValidationError("Condition must be a string or structured dictionary")
        
        # Extract actions
        actions = rule_dict.get('actions') or rule_dict.get('then', {})
        if not isinstance(actions, dict):
            raise ValidationError("Actions must be a dictionary")
        
        if not actions:
            raise ValidationError("Actions cannot be empty")
        
        # Create rule with validation
        rule = Rule(
            id=str(rule_dict['id']),
            priority=int(rule_dict.get('priority', 0)),
            condition=condition.strip(),
            actions=actions,
            tags=list(rule_dict.get('tags', [])),
            triggers=list(rule_dict.get('triggers', []))
        )
        
        return rule 