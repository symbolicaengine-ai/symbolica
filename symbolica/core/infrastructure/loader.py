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
from .schema_validator import SchemaValidator


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
    """Handles loading and parsing rules from various sources with strict schema validation."""
    
    def __init__(self, strict_validation: bool = True):
        """Initialize RuleLoader.
        
        Args:
            strict_validation: If True, enforces strict schema validation
        """
        self.condition_parser = ConditionParser()
        self.schema_validator = SchemaValidator()
        self.strict_validation = strict_validation
    
    def from_yaml(self, yaml_content: str) -> List[Rule]:
        """Create rules from YAML string with schema validation."""
        return self._parse_yaml_rules(yaml_content)
    
    def from_file(self, file_path: Union[str, Path]) -> List[Rule]:
        """Create rules from YAML file with schema validation."""
        try:
            with open(file_path, 'r') as f:
                yaml_content = f.read()
            return self.from_yaml(yaml_content)
        except FileNotFoundError:
            raise ValidationError(f"File not found: {file_path}")
        except Exception as e:
            raise ValidationError(f"Error reading file {file_path}: {e}")
    
    def from_directory(self, directory_path: Union[str, Path]) -> List[Rule]:
        """Create rules from directory containing YAML files with schema validation."""
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
    
    def validate_yaml_schema(self, yaml_content: str) -> Dict[str, Any]:
        """Validate YAML content against schema and return parsed data.
        
        Args:
            yaml_content: YAML content string
            
        Returns:
            Parsed and validated YAML data
            
        Raises:
            ValidationError: If schema validation fails
        """
        if not yaml_content or not yaml_content.strip():
            raise ValidationError("YAML content cannot be empty")
        
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML syntax: {e}")
        
        if not data:
            raise ValidationError("YAML content is empty or invalid")
        
        # Perform schema validation if enabled
        if self.strict_validation:
            self.schema_validator.validate_yaml_structure(data)
            
            # Validate each rule structure
            if 'rules' in data:
                for i, rule_dict in enumerate(data['rules']):
                    self.schema_validator.validate_rule_structure(rule_dict, i)
        
        return data
    
    def get_schema_documentation(self) -> str:
        """Get schema documentation for users.
        
        Returns:
            Human-readable schema documentation
        """
        return self.schema_validator.generate_schema_documentation()
    
    def get_reserved_keywords(self) -> set:
        """Get set of reserved keywords.
        
        Returns:
            Set of reserved keywords
        """
        return self.schema_validator.get_reserved_keywords()
    
    def _parse_yaml_rules(self, yaml_content: str) -> List[Rule]:
        """Parse YAML content into rules with comprehensive validation."""
        # First validate the schema
        data = self.validate_yaml_schema(yaml_content)
        
        # Legacy validation fallback for basic structure (if strict validation disabled)
        if not self.strict_validation:
            self._legacy_validation(data)
        
        rules = []
        for i, rule_dict in enumerate(data['rules']):
            try:
                rule = self._parse_single_rule(rule_dict, i)
                rules.append(rule)
            except Exception as e:
                raise ValidationError(f"Error parsing rule at index {i}: {e}")
        
        return rules
    
    def _parse_single_rule(self, rule_dict: Dict[str, Any], rule_index: int) -> Rule:
        """Parse a single rule dictionary into a Rule object with enhanced validation."""
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
        
        # Extract facts (optional)
        facts = rule_dict.get('facts', {})
        if not isinstance(facts, dict):
            raise ValidationError("Facts must be a dictionary")
        
        # Additional validation for enabled field
        enabled = rule_dict.get('enabled', True)
        if not isinstance(enabled, bool):
            raise ValidationError("'enabled' field must be a boolean")
        
        # Skip disabled rules
        if not enabled:
            # Create a disabled rule marker (could be filtered out later)
            pass
        
        # Create rule with validation
        rule = Rule(
            id=str(rule_dict['id']),
            priority=int(rule_dict.get('priority', 0)),
            condition=condition.strip(),
            actions=actions,
            facts=facts,
            tags=list(rule_dict.get('tags', [])),
            triggers=list(rule_dict.get('triggers', []))
        )
        
        return rule
    
    def _legacy_validation(self, data: Dict[str, Any]) -> None:
        """Legacy validation for when strict validation is disabled."""
        if not isinstance(data, dict):
            raise ValidationError("YAML must contain a dictionary")
        
        if 'rules' not in data:
            raise ValidationError("YAML must contain 'rules' key")
        
        if not isinstance(data['rules'], list):
            raise ValidationError("'rules' must be a list")
        
        if not data['rules']:
            raise ValidationError("Rules list cannot be empty") 