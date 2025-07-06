"""
Rule Loading
===========

Load rules from various sources (YAML, JSON, files, etc.)
"""

import json
import yaml
from pathlib import Path
from typing import List, Dict, Any, Union

from ..core import (
    Rule, RuleLoader, LoadError,
    rule_id, priority, condition, action_set, action_call
)


class DefaultRuleLoader(RuleLoader):
    """
    Default rule loader supporting multiple formats.
    
    Supported formats:
    - YAML strings/files
    - JSON strings/files
    - Python dictionaries
    - Direct Rule objects
    """
    
    def load(self, source: Union[str, Path, Dict[str, Any], List[Dict[str, Any]]]) -> List[Rule]:
        """Load rules from various sources."""
        try:
            if isinstance(source, (str, Path)):
                return self._load_from_path_or_string(source)
            elif isinstance(source, dict):
                return self._load_from_dict(source)
            elif isinstance(source, list):
                return self._load_from_list(source)
            else:
                raise LoadError(f"Unsupported source type: {type(source)}")
        
        except Exception as e:
            if isinstance(e, LoadError):
                raise
            raise LoadError(f"Failed to load rules: {e}") from e
    
    def supported_formats(self) -> List[str]:
        """Get list of supported formats."""
        return ['yaml', 'json', 'dict', 'list']
    
    def _load_from_path_or_string(self, source: Union[str, Path]) -> List[Rule]:
        """Load from file path or string content."""
        if isinstance(source, Path) or (isinstance(source, str) and len(source) < 500 and '/' in source):
            # Treat as file path
            return self._load_from_file(Path(source))
        else:
            # Treat as string content
            return self._load_from_string(source)
    
    def _load_from_file(self, file_path: Path) -> List[Rule]:
        """Load rules from file."""
        if not file_path.exists():
            raise LoadError(f"Rule file not found: {file_path}", source=str(file_path))
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            if file_path.suffix.lower() in ['.yaml', '.yml']:
                return self._load_from_yaml(content)
            elif file_path.suffix.lower() == '.json':
                return self._load_from_json(content)
            else:
                # Try to auto-detect format
                return self._load_from_string(content)
        
        except Exception as e:
            raise LoadError(f"Failed to read file: {e}", source=str(file_path)) from e
    
    def _load_from_string(self, content: str) -> List[Rule]:
        """Load rules from string content (auto-detect format)."""
        content = content.strip()
        
        if not content:
            return []
        
        # Try YAML first (more flexible)
        try:
            return self._load_from_yaml(content)
        except Exception:
            pass
        
        # Try JSON
        try:
            return self._load_from_json(content)
        except Exception:
            pass
        
        raise LoadError("Could not parse content as YAML or JSON", source=content[:100])
    
    def _load_from_yaml(self, content: str) -> List[Rule]:
        """Load rules from YAML content."""
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                return self._load_from_dict(data)
            elif isinstance(data, list):
                return self._load_from_list(data)
            else:
                raise LoadError(f"YAML content must be dict or list, got {type(data)}")
        except yaml.YAMLError as e:
            raise LoadError(f"Invalid YAML: {e}", format="yaml") from e
    
    def _load_from_json(self, content: str) -> List[Rule]:
        """Load rules from JSON content."""
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return self._load_from_dict(data)
            elif isinstance(data, list):
                return self._load_from_list(data)
            else:
                raise LoadError(f"JSON content must be dict or list, got {type(data)}")
        except json.JSONDecodeError as e:
            raise LoadError(f"Invalid JSON: {e}", format="json") from e
    
    def _load_from_dict(self, data: Dict[str, Any]) -> List[Rule]:
        """Load rules from dictionary."""
        if 'rules' in data:
            # Standard format with rules array
            return self._load_from_list(data['rules'])
        else:
            # Treat the entire dict as a single rule
            return [self._dict_to_rule(data)]
    
    def _load_from_list(self, data: List[Dict[str, Any]]) -> List[Rule]:
        """Load rules from list of dictionaries."""
        rules = []
        for i, rule_data in enumerate(data):
            try:
                rule = self._dict_to_rule(rule_data)
                rules.append(rule)
            except Exception as e:
                raise LoadError(f"Failed to parse rule {i}: {e}") from e
        return rules
    
    def _dict_to_rule(self, data: Dict[str, Any]) -> Rule:
        """Convert dictionary to Rule object."""
        # Extract required fields
        rule_id_str = data.get('id') or data.get('name')
        if not rule_id_str:
            raise LoadError("Rule must have 'id' or 'name'")
        
        condition_expr = data.get('condition') or data.get('if')
        if not condition_expr:
            raise LoadError("Rule must have 'condition' or 'if'")
        
        # Extract priority
        rule_priority = data.get('priority', 50)
        
        # Extract actions
        actions = []
        
        # Handle 'then' clause
        if 'then' in data:
            then_data = data['then']
            if isinstance(then_data, dict):
                # Single action
                actions.append(self._dict_to_action(then_data))
            elif isinstance(then_data, list):
                # Multiple actions
                for action_data in then_data:
                    actions.append(self._dict_to_action(action_data))
        
        # Handle 'actions' clause
        if 'actions' in data:
            actions_data = data['actions']
            if isinstance(actions_data, list):
                for action_data in actions_data:
                    actions.append(self._dict_to_action(action_data))
        
        # Handle simple set actions directly in rule
        for key, value in data.items():
            if key not in ['id', 'name', 'condition', 'if', 'priority', 'then', 'actions', 'tags']:
                actions.append(action_set(**{key: value}))
        
        if not actions:
            raise LoadError("Rule must have at least one action")
        
        # Extract tags
        tags = data.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]
        
        return Rule(
            id=rule_id(rule_id_str),
            priority=priority(rule_priority),
            condition=condition(condition_expr),
            actions=actions,
            tags=frozenset(tags)
        )
    
    def _dict_to_action(self, data: Dict[str, Any]) -> Any:
        """Convert dictionary to Action object."""
        from ..core import Action
        
        if 'type' in data:
            # Explicit action type
            action_type = data['type']
            params = {k: v for k, v in data.items() if k != 'type'}
            return Action(action_type, params)
        
        elif 'set' in data:
            # Set action
            return action_set(**data['set'])
        
        elif 'call' in data:
            # Call action
            return action_call(data['call'], **data.get('params', {}))
        
        else:
            # Assume it's a set action
            return action_set(**data)


# Factory function
def create_loader(loader_type: str = "default") -> RuleLoader:
    """Create rule loader of specified type."""
    if loader_type == "default":
        return DefaultRuleLoader()
    else:
        raise LoadError(f"Unknown loader type: {loader_type}")


# Example YAML format
EXAMPLE_YAML = """
rules:
  - id: "high_value_customer"
    priority: 100
    condition: "customer_value > 1000 and customer_tier == 'premium'"
    then:
      type: "set"
      priority_support: true
      discount_rate: 0.15
    tags: ["customer", "vip"]
  
  - id: "new_customer_welcome"
    priority: 50
    condition: "is_new_customer and days_since_signup < 7"
    actions:
      - type: "set"
        welcome_bonus: 100
      - type: "call"
        function: "send_welcome_email"
        params:
          template: "new_customer"
""" 