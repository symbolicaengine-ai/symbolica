"""
YAML Schema Validation
======================

Enforces strict YAML structure and reserved keyword validation for rule files.
Ensures consistent AST structure and prevents user confusion.
"""

from typing import Dict, Any, List, Set, Union
from .exceptions import ValidationError


class SchemaValidator:
    """Enforces YAML schema and reserved keyword validation."""
    
    # Top-level required keys
    REQUIRED_TOP_LEVEL_KEYS = frozenset({'rules'})
    
    # Top-level allowed keys (optional ones user can add)
    ALLOWED_TOP_LEVEL_KEYS = frozenset({
        'rules',        # Required: List of rules
        'version',      # Optional: Schema version
        'description',  # Optional: File description
        'metadata'      # Optional: Additional metadata
    })
    
    # Rule-level required fields
    REQUIRED_RULE_FIELDS = frozenset({'id', 'condition', 'actions'})
    
    # Rule-level allowed fields
    ALLOWED_RULE_FIELDS = frozenset({
        'id',           # Required: Unique identifier
        'priority',     # Optional: Execution priority (integer)
        'condition',    # Required: Condition string or dict
        'if',           # Alternative to 'condition'
        'facts',        # Optional: Intermediate state (dict)
        'actions',      # Required: Final outputs (dict)
        'then',         # Alternative to 'actions'
        'triggers',     # Optional: Rules to trigger (list)
        'tags',         # Optional: Metadata tags (list)
        'description',  # Optional: Rule description
        'enabled'       # Optional: Enable/disable flag
    })
    
    # Structured condition keywords
    CONDITION_KEYWORDS = frozenset({'all', 'any', 'not'})
    
    # System reserved keywords that cannot be used as identifiers
    SYSTEM_RESERVED_KEYWORDS = frozenset({
        # Core system fields
        'rules', 'condition', 'actions', 'facts', 'triggers', 'tags', 'priority', 'id',
        'if', 'then', 'all', 'any', 'not', 'enabled', 'description', 'metadata', 'version',
        
        # Python built-ins and operators
        'True', 'False', 'None', 'and', 'or', 'not', 'in', 'is', 'if', 'else', 'elif',
        'for', 'while', 'def', 'class', 'import', 'from', 'return', 'yield', 'try', 
        'except', 'finally', 'with', 'as', 'pass', 'break', 'continue', 'lambda', 
        'global', 'nonlocal', 'assert', 'del', 'raise',
        
        # Built-in functions commonly used in expressions
        'len', 'sum', 'abs', 'min', 'max', 'round', 'int', 'float', 'str', 'bool',
        'list', 'dict', 'set', 'tuple', 'range', 'enumerate', 'zip', 'map', 'filter',
        'startswith', 'endswith', 'contains', 'upper', 'lower', 'strip', 'split',
        
        # Temporal functions
        'recent_avg', 'recent_max', 'recent_min', 'recent_count', 'sustained_above', 
        'sustained_below', 'ttl_fact', 'has_ttl_fact',
        
        # Mathematical constants and functions
        'pi', 'e', 'inf', 'nan', 'sin', 'cos', 'tan', 'sqrt', 'log', 'exp', 'pow'
    })
    
    # Valid data types for rule fields
    FIELD_TYPE_VALIDATORS = {
        'id': lambda x: isinstance(x, str) and x.strip(),
        'priority': lambda x: isinstance(x, int),
        'condition': lambda x: isinstance(x, (str, dict)),
        'if': lambda x: isinstance(x, (str, dict)),
        'facts': lambda x: isinstance(x, dict),
        'actions': lambda x: isinstance(x, dict),
        'then': lambda x: isinstance(x, dict),
        'triggers': lambda x: isinstance(x, list) and all(isinstance(item, str) for item in x),
        'tags': lambda x: isinstance(x, list) and all(isinstance(item, str) for item in x),
        'description': lambda x: isinstance(x, str),
        'enabled': lambda x: isinstance(x, bool),
        'version': lambda x: isinstance(x, str),
        'metadata': lambda x: isinstance(x, dict)
    }
    
    def validate_yaml_structure(self, data: Any) -> None:
        """Validate the overall YAML structure.
        
        Args:
            data: Parsed YAML data
            
        Raises:
            ValidationError: If structure is invalid
        """
        # Must be a dictionary
        if not isinstance(data, dict):
            raise ValidationError(
                "YAML root must be a dictionary. "
                f"Got {type(data).__name__}."
            )
        
        # Check for required top-level keys
        missing_keys = self.REQUIRED_TOP_LEVEL_KEYS - set(data.keys())
        if missing_keys:
            raise ValidationError(
                f"Missing required top-level keys: {sorted(missing_keys)}. "
                f"Required keys are: {sorted(self.REQUIRED_TOP_LEVEL_KEYS)}"
            )
        
        # Check for unknown top-level keys
        unknown_keys = set(data.keys()) - self.ALLOWED_TOP_LEVEL_KEYS
        if unknown_keys:
            raise ValidationError(
                f"Unknown top-level keys: {sorted(unknown_keys)}. "
                f"Allowed keys are: {sorted(self.ALLOWED_TOP_LEVEL_KEYS)}"
            )
        
        # Validate top-level field types
        for key, value in data.items():
            if key in self.FIELD_TYPE_VALIDATORS:
                if not self.FIELD_TYPE_VALIDATORS[key](value):
                    expected_type = self._get_expected_type_description(key)
                    raise ValidationError(
                        f"Top-level field '{key}' has invalid type. "
                        f"Expected {expected_type}, got {type(value).__name__}."
                    )
        
        # Special validation for rules list
        if 'rules' in data:
            self._validate_rules_list(data['rules'])
    
    def validate_rule_structure(self, rule_dict: Dict[str, Any], rule_index: int) -> None:
        """Validate individual rule structure.
        
        Args:
            rule_dict: Rule dictionary
            rule_index: Index of rule in list (for error messages)
            
        Raises:
            ValidationError: If rule structure is invalid
        """
        if not isinstance(rule_dict, dict):
            raise ValidationError(
                f"Rule at index {rule_index} must be a dictionary. "
                f"Got {type(rule_dict).__name__}."
            )
        
        # Check for required fields
        missing_fields = self.REQUIRED_RULE_FIELDS - set(rule_dict.keys())
        if missing_fields:
            # Handle alternative field names
            alternatives = {
                'condition': rule_dict.get('if'),
                'actions': rule_dict.get('then')
            }
            
            actual_missing = []
            for field in missing_fields:
                if field not in alternatives or alternatives[field] is None:
                    actual_missing.append(field)
            
            if actual_missing:
                raise ValidationError(
                    f"Rule at index {rule_index} missing required fields: {sorted(actual_missing)}. "
                    f"Required fields are: {sorted(self.REQUIRED_RULE_FIELDS)}. "
                    f"Alternative field names: 'if' for 'condition', 'then' for 'actions'."
                )
        
        # Check for unknown fields
        unknown_fields = set(rule_dict.keys()) - self.ALLOWED_RULE_FIELDS
        if unknown_fields:
            raise ValidationError(
                f"Rule at index {rule_index} has unknown fields: {sorted(unknown_fields)}. "
                f"Allowed fields are: {sorted(self.ALLOWED_RULE_FIELDS)}"
            )
        
        # Validate field types
        for field, value in rule_dict.items():
            if field in self.FIELD_TYPE_VALIDATORS:
                if not self.FIELD_TYPE_VALIDATORS[field](value):
                    expected_type = self._get_expected_type_description(field)
                    raise ValidationError(
                        f"Rule at index {rule_index}, field '{field}' has invalid type. "
                        f"Expected {expected_type}, got {type(value).__name__}."
                    )
        
        # Validate rule ID is not reserved
        if 'id' in rule_dict:
            self.validate_identifier(rule_dict['id'], f"Rule ID at index {rule_index}")
        
        # Validate structured conditions
        condition = rule_dict.get('condition') or rule_dict.get('if')
        if isinstance(condition, dict):
            self._validate_structured_condition(condition, rule_index)
        
        # Validate fact and action names
        if 'facts' in rule_dict:
            self._validate_fact_action_names(rule_dict['facts'], f"Rule at index {rule_index}, facts")
        
        actions = rule_dict.get('actions') or rule_dict.get('then', {})
        self._validate_fact_action_names(actions, f"Rule at index {rule_index}, actions")
    
    def validate_identifier(self, identifier: str, context: str) -> None:
        """Validate that an identifier is not a reserved keyword.
        
        Args:
            identifier: The identifier to validate
            context: Context description for error messages
            
        Raises:
            ValidationError: If identifier is reserved
        """
        if not isinstance(identifier, str):
            raise ValidationError(f"{context}: identifier must be a string")
        
        if not identifier.strip():
            raise ValidationError(f"{context}: identifier cannot be empty or whitespace")
        
        if identifier in self.SYSTEM_RESERVED_KEYWORDS:
            raise ValidationError(
                f"{context}: '{identifier}' is a reserved keyword and cannot be used. "
                f"Reserved keywords include system fields, Python built-ins, and function names."
            )
        
        # Additional validation for Python identifier rules
        if not identifier.isidentifier():
            raise ValidationError(
                f"{context}: '{identifier}' is not a valid identifier. "
                f"Identifiers must start with a letter or underscore, "
                f"followed by letters, digits, or underscores."
            )
    
    def get_reserved_keywords(self) -> Set[str]:
        """Get the complete set of reserved keywords.
        
        Returns:
            Set of all reserved keywords
        """
        return self.SYSTEM_RESERVED_KEYWORDS.copy()
    
    def _validate_rules_list(self, rules: Any) -> None:
        """Validate the rules list structure."""
        if not isinstance(rules, list):
            raise ValidationError(
                f"'rules' must be a list. Got {type(rules).__name__}."
            )
        
        if not rules:
            raise ValidationError("'rules' list cannot be empty.")
        
        # Validate each rule has basic structure
        for i, rule in enumerate(rules):
            if not isinstance(rule, dict):
                raise ValidationError(
                    f"Rule at index {i} must be a dictionary. "
                    f"Got {type(rule).__name__}."
                )
    
    def _validate_structured_condition(self, condition_dict: Dict[str, Any], rule_index: int) -> None:
        """Validate structured condition keywords."""
        for key in condition_dict.keys():
            if key not in self.CONDITION_KEYWORDS:
                raise ValidationError(
                    f"Rule at index {rule_index}: unknown condition keyword '{key}'. "
                    f"Valid condition keywords are: {sorted(self.CONDITION_KEYWORDS)}"
                )
    
    def _validate_fact_action_names(self, items: Dict[str, Any], context: str) -> None:
        """Validate fact and action names are not reserved."""
        for name in items.keys():
            try:
                self.validate_identifier(name, f"{context}, field '{name}'")
            except ValidationError as e:
                # Re-raise with more specific context
                raise ValidationError(str(e))
    
    def _get_expected_type_description(self, field: str) -> str:
        """Get human-readable type description for a field."""
        type_descriptions = {
            'id': 'non-empty string',
            'priority': 'integer',
            'condition': 'string or dictionary',
            'if': 'string or dictionary',
            'facts': 'dictionary',
            'actions': 'dictionary',
            'then': 'dictionary',
            'triggers': 'list of strings',
            'tags': 'list of strings',
            'description': 'string',
            'enabled': 'boolean',
            'version': 'string',
            'metadata': 'dictionary',
            'rules': 'list'
        }
        return type_descriptions.get(field, 'unknown type')
    
    def generate_schema_documentation(self) -> str:
        """Generate human-readable schema documentation.
        
        Returns:
            Formatted schema documentation
        """
        doc = []
        doc.append("Symbolica YAML Schema")
        doc.append("=" * 21)
        doc.append("")
        
        doc.append("Top-level Structure:")
        doc.append("-------------------")
        doc.append("rules: []           # Required: List of rules")
        doc.append("version: \"1.0\"       # Optional: Schema version")
        doc.append("description: \"...\"   # Optional: File description")
        doc.append("metadata: {}        # Optional: Additional metadata")
        doc.append("")
        
        doc.append("Rule Structure:")
        doc.append("---------------")
        doc.append("- id: \"rule_name\"     # Required: Unique identifier")
        doc.append("  priority: 100       # Optional: Execution priority (integer)")
        doc.append("  condition: \"...\"    # Required: String or structured dict")
        doc.append("  facts: {}           # Optional: Intermediate state (dict)")
        doc.append("  actions: {}         # Required: Final outputs (dict)")
        doc.append("  triggers: []        # Optional: Rules to trigger (list)")
        doc.append("  tags: []            # Optional: Metadata tags (list)")
        doc.append("  description: \"...\"  # Optional: Rule description")
        doc.append("  enabled: true       # Optional: Enable/disable flag")
        doc.append("")
        
        doc.append("Reserved Keywords:")
        doc.append("-" * 17)
        doc.append("The following keywords are reserved and cannot be used")
        doc.append("as rule IDs, fact names, or action names:")
        doc.append("")
        
        # Group reserved keywords by category
        keywords = sorted(self.SYSTEM_RESERVED_KEYWORDS)
        doc.append("(Sample of reserved keywords - total: {})".format(len(keywords)))
        doc.append("")
        
        # Show first 30 keywords as examples
        for i, keyword in enumerate(keywords[:30]):
            if i % 6 == 0:
                doc.append("")
            if i % 6 == 0:
                line = f"  {keyword:<15}"
            else:
                line += f"{keyword:<15}"
            
            if (i + 1) % 6 == 0 or i == len(keywords[:30]) - 1:
                doc.append(line)
        
        doc.append("")
        doc.append("... and {} more keywords".format(len(keywords) - 30))
        
        return "\n".join(doc) 