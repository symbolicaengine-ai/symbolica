"""
Schema Constants
================

Centralized schema configuration and constants.
Extracted from SchemaValidator to follow Single Responsibility Principle.
"""

from typing import Set, Dict, Callable, Any


class SchemaConstants:
    """Centralized schema constants and configuration."""
    
    # Top-level required keys
    REQUIRED_TOP_LEVEL_KEYS: Set[str] = frozenset({'rules'})
    
    # Top-level allowed keys (optional ones user can add)
    ALLOWED_TOP_LEVEL_KEYS: Set[str] = frozenset({
        'rules',        # Required: List of rules
        'version',      # Optional: Schema version
        'description',  # Optional: File description
        'metadata'      # Optional: Additional metadata
    })
    
    # Rule-level required fields
    REQUIRED_RULE_FIELDS: Set[str] = frozenset({'id', 'condition', 'actions'})
    
    # Rule-level allowed fields
    ALLOWED_RULE_FIELDS: Set[str] = frozenset({
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
    CONDITION_KEYWORDS: Set[str] = frozenset({'all', 'any', 'not'})
    
    # System reserved keywords that cannot be used as identifiers
    SYSTEM_RESERVED_KEYWORDS: Set[str] = frozenset({
        # Core system fields
        'rules', 'condition', 'actions', 'facts', 'triggers', 'tags', 'priority', 'id',
        'if', 'then', 'all', 'any', 'not', 'enabled', 'description', 'metadata', 'version',
        
        # Python built-ins and operators that would break expressions
        'True', 'False', 'None', 'and', 'or', 'not', 'in', 'is', 'if', 'else', 'elif',
        'for', 'while', 'def', 'class', 'import', 'from', 'return', 'yield', 'try', 
        'except', 'finally', 'with', 'as', 'pass', 'break', 'continue', 'lambda', 
        'global', 'nonlocal', 'assert', 'del', 'raise',
        
        # Built-in functions that are actually implemented in our evaluator
        'len', 'sum', 'abs', 'startswith', 'endswith', 'contains',
        
        # Alternative boolean/null representations
        'true', 'false', 'null',
        
        # Temporal functions (system provided)
        'recent_avg', 'recent_max', 'recent_min', 'recent_count', 'sustained_above', 
        'sustained_below', 'ttl_fact', 'has_ttl_fact', 'sustained'
    })
    
    # Valid data types for rule fields
    FIELD_TYPE_VALIDATORS: Dict[str, Callable[[Any], bool]] = {
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
    
    # Type descriptions for error messages
    TYPE_DESCRIPTIONS: Dict[str, str] = {
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
    
    @classmethod
    def get_expected_type_description(cls, field: str) -> str:
        """Get human-readable type description for a field."""
        return cls.TYPE_DESCRIPTIONS.get(field, 'unknown type') 