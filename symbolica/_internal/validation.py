"""
Enhanced Validation and Error Handling
======================================

Comprehensive validation system with:
- Contextual error messages with line numbers and suggestions
- Input validation for facts and rules with type checking
- Field reference validation and suggestions
- Common mistake detection and helpful guidance
- Progressive validation levels (warning -> error)
"""

import re
import ast
import json
from typing import Dict, Any, List, Set, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from ..core import (
    Rule, RuleSet, Facts, ValidationError, EvaluationError,
    rule_id, priority, condition, action_set
)


class ValidationLevel(Enum):
    """Validation severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """A validation issue with context and suggestions."""
    level: ValidationLevel
    message: str
    context: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    rule_id: Optional[str] = None
    field_name: Optional[str] = None
    suggestion: Optional[str] = None
    fix_hint: Optional[str] = None
    
    def __str__(self) -> str:
        parts = [f"[{self.level.value.upper()}] {self.message}"]
        
        if self.context:
            parts.append(f"Context: {self.context}")
        
        if self.line_number:
            parts.append(f"Line: {self.line_number}")
        
        if self.rule_id:
            parts.append(f"Rule: {self.rule_id}")
        
        if self.field_name:
            parts.append(f"Field: {self.field_name}")
        
        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")
        
        if self.fix_hint:
            parts.append(f"Fix: {self.fix_hint}")
        
        return " | ".join(parts)


@dataclass
class ValidationResult:
    """Result of validation with categorized issues."""
    valid: bool
    issues: List[ValidationIssue]
    errors: List[ValidationIssue]
    warnings: List[ValidationIssue]
    infos: List[ValidationIssue]
    
    @classmethod
    def from_issues(cls, issues: List[ValidationIssue]) -> 'ValidationResult':
        """Create validation result from issues list."""
        errors = [i for i in issues if i.level == ValidationLevel.ERROR]
        warnings = [i for i in issues if i.level == ValidationLevel.WARNING]
        infos = [i for i in issues if i.level == ValidationLevel.INFO]
        
        return cls(
            valid=len(errors) == 0,
            issues=issues,
            errors=errors,
            warnings=warnings,
            infos=infos
        )


class EnhancedValidator:
    """
    Comprehensive validator with contextual error reporting.
    
    Features:
    - Detailed error messages with context
    - Field reference validation
    - Type checking and coercion suggestions
    - Common mistake detection
    - Progressive validation levels
    """
    
    def __init__(self, strict: bool = False):
        self.strict = strict
        self._common_field_names = set()
        self._seen_expressions = set()
        self._field_types: Dict[str, Set[type]] = {}
    
    def validate_facts(self, facts_data: Any, expected_fields: Optional[Set[str]] = None) -> ValidationResult:
        """
        Validate facts input with helpful error messages.
        
        Args:
            facts_data: Facts to validate
            expected_fields: Optional set of expected field names
            
        Returns:
            ValidationResult with issues and suggestions
        """
        issues = []
        
        # Check if facts is a dictionary
        if not isinstance(facts_data, dict):
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Facts must be a dictionary, got {type(facts_data).__name__}",
                suggestion="Provide facts as a dictionary: {'field_name': value, ...}",
                fix_hint="Convert your data to a dictionary format"
            ))
            return ValidationResult.from_issues(issues)
        
        # Check for empty facts
        if not facts_data:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message="Facts dictionary is empty",
                suggestion="Add some facts for rules to evaluate against"
            ))
        
        # Validate individual fields
        for field_name, value in facts_data.items():
            field_issues = self._validate_fact_field(field_name, value, expected_fields)
            issues.extend(field_issues)
        
        # Check for missing expected fields
        if expected_fields:
            missing_fields = expected_fields - set(facts_data.keys())
            if missing_fields:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    message=f"Missing expected fields: {', '.join(sorted(missing_fields))}",
                    suggestion="Add these fields to your facts or update your rules",
                    fix_hint="These fields are referenced by your rules but not provided in facts"
                ))
        
        # Update field type tracking
        self._update_field_types(facts_data)
        
        return ValidationResult.from_issues(issues)
    
    def validate_expression(self, expression: str, context: str = "", 
                          available_fields: Optional[Set[str]] = None) -> ValidationResult:
        """
        Validate expression syntax and semantics with detailed feedback.
        
        Args:
            expression: Expression to validate
            context: Context for error reporting (e.g., rule ID)
            available_fields: Set of available field names
            
        Returns:
            ValidationResult with detailed issues
        """
        issues = []
        
        if not expression or not expression.strip():
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message="Expression cannot be empty",
                context=context,
                suggestion="Provide a valid expression like 'field > 10' or 'status == \"active\"'"
            ))
            return ValidationResult.from_issues(issues)
        
        # Check for basic syntax issues
        syntax_issues = self._check_expression_syntax(expression, context)
        issues.extend(syntax_issues)
        
        # Extract and validate field references
        field_issues = self._validate_field_references(expression, context, available_fields)
        issues.extend(field_issues)
        
        # Check for common mistakes
        mistake_issues = self._detect_common_mistakes(expression, context)
        issues.extend(mistake_issues)
        
        # Check expression complexity
        complexity_issues = self._check_expression_complexity(expression, context)
        issues.extend(complexity_issues)
        
        return ValidationResult.from_issues(issues)
    
    def validate_rule(self, rule_data: Dict[str, Any], 
                     context: str = "", line_number: Optional[int] = None) -> ValidationResult:
        """
        Validate a rule with comprehensive checks.
        
        Args:
            rule_data: Rule dictionary to validate
            context: Context for error reporting
            line_number: Line number in source file
            
        Returns:
            ValidationResult with detailed issues
        """
        issues = []
        
        # Validate required fields
        required_fields = ['id', 'if', 'then']
        for field in required_fields:
            if field not in rule_data:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"Missing required field '{field}'",
                    context=context,
                    line_number=line_number,
                    suggestion=f"Add the '{field}' field to your rule",
                    fix_hint=f"Example: {field}: <value>"
                ))
        
        if issues:  # Can't continue validation without required fields
            return ValidationResult.from_issues(issues)
        
        # Validate rule ID
        rule_id_issues = self._validate_rule_id(rule_data['id'], context, line_number)
        issues.extend(rule_id_issues)
        
        # Validate priority
        if 'priority' in rule_data:
            priority_issues = self._validate_priority(rule_data['priority'], context, line_number)
            issues.extend(priority_issues)
        
        # Validate condition
        condition_issues = self.validate_expression(
            rule_data['if'], 
            f"{context}.condition",
            self._common_field_names
        )
        # Update context for condition issues
        for issue in condition_issues.issues:
            issue.rule_id = rule_data.get('id')
            issue.line_number = line_number
        issues.extend(condition_issues.issues)
        
        # Validate actions
        actions_issues = self._validate_actions(rule_data['then'], context, line_number)
        issues.extend(actions_issues)
        
        # Validate tags
        if 'tags' in rule_data:
            tags_issues = self._validate_tags(rule_data['tags'], context, line_number)
            issues.extend(tags_issues)
        
        return ValidationResult.from_issues(issues)
    
    def validate_rule_set(self, rules: List[Dict[str, Any]], 
                         context: str = "ruleset") -> ValidationResult:
        """
        Validate an entire rule set with cross-rule analysis.
        
        Args:
            rules: List of rule dictionaries
            context: Context for error reporting
            
        Returns:
            ValidationResult with comprehensive analysis
        """
        issues = []
        
        if not rules:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message="Rule set is empty",
                context=context,
                suggestion="Add some rules to make the rule set functional"
            ))
            return ValidationResult.from_issues(issues)
        
        # Validate individual rules
        rule_ids = set()
        for i, rule_data in enumerate(rules):
            rule_context = f"{context}.rule[{i}]"
            rule_issues = self.validate_rule(rule_data, rule_context, i + 1)
            issues.extend(rule_issues.issues)
            
            # Track rule IDs for duplicate detection
            if 'id' in rule_data:
                if rule_data['id'] in rule_ids:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        message=f"Duplicate rule ID: {rule_data['id']}",
                        context=rule_context,
                        line_number=i + 1,
                        suggestion="Use unique rule IDs",
                        fix_hint="Change one of the rule IDs to be unique"
                    ))
                rule_ids.add(rule_data['id'])
        
        # Cross-rule analysis
        cross_issues = self._analyze_cross_rule_patterns(rules, context)
        issues.extend(cross_issues)
        
        return ValidationResult.from_issues(issues)
    
    def _validate_fact_field(self, field_name: str, value: Any, 
                           expected_fields: Optional[Set[str]] = None) -> List[ValidationIssue]:
        """Validate a single fact field."""
        issues = []
        
        # Validate field name
        if not isinstance(field_name, str):
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Field name must be string, got {type(field_name).__name__}",
                field_name=str(field_name),
                fix_hint="Ensure all field names are strings"
            ))
            return issues
        
        if not field_name:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message="Field name cannot be empty",
                suggestion="Use descriptive field names like 'customer_id', 'amount', etc."
            ))
            return issues
        
        # Check field name format
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', field_name):
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message=f"Field name '{field_name}' contains special characters",
                field_name=field_name,
                suggestion="Use alphanumeric characters and underscores only",
                fix_hint="Example: 'customer_id' instead of 'customer-id' or 'customer.id'"
            ))
        
        # Check for reserved words
        reserved_words = {'and', 'or', 'not', 'in', 'is', 'if', 'else', 'True', 'False', 'None'}
        if field_name in reserved_words:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Field name '{field_name}' is a reserved word",
                field_name=field_name,
                suggestion="Use a different field name",
                fix_hint=f"Try '{field_name}_value' or 'is_{field_name}' instead"
            ))
        
        # Validate field value
        value_issues = self._validate_fact_value(field_name, value)
        issues.extend(value_issues)
        
        # Track common field names
        self._common_field_names.add(field_name)
        
        return issues
    
    def _validate_fact_value(self, field_name: str, value: Any) -> List[ValidationIssue]:
        """Validate a fact value."""
        issues = []
        
        # Check for problematic types
        if isinstance(value, (complex, type, type(lambda: None))):
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Unsupported value type {type(value).__name__} for field '{field_name}'",
                field_name=field_name,
                suggestion="Use basic types: str, int, float, bool, list, dict, or None"
            ))
        
        # Check for very large values
        if isinstance(value, str) and len(value) > 10000:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message=f"Very large string value for field '{field_name}' ({len(value)} characters)",
                field_name=field_name,
                suggestion="Consider if such large values are necessary"
            ))
        
        elif isinstance(value, list) and len(value) > 1000:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message=f"Very large list for field '{field_name}' ({len(value)} items)",
                field_name=field_name,
                suggestion="Consider if such large lists are necessary for rule evaluation"
            ))
        
        # Check for NaN or infinity in numeric values
        if isinstance(value, float):
            import math
            if math.isnan(value):
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"Field '{field_name}' contains NaN",
                    field_name=field_name,
                    suggestion="Replace NaN with None or a default numeric value"
                ))
            elif math.isinf(value):
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    message=f"Field '{field_name}' contains infinity",
                    field_name=field_name,
                    suggestion="Consider using a large finite number instead"
                ))
        
        return issues
    
    def _check_expression_syntax(self, expression: str, context: str) -> List[ValidationIssue]:
        """Check basic expression syntax."""
        issues = []
        
        try:
            # Try to parse as Python expression
            ast.parse(expression.strip(), mode='eval')
        except SyntaxError as e:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Syntax error in expression: {e.msg}",
                context=context,
                line_number=getattr(e, 'lineno', None),
                column=getattr(e, 'offset', None),
                suggestion="Check for missing quotes, parentheses, or operators",
                fix_hint="Use valid Python expression syntax"
            ))
        
        # Check for balanced parentheses
        if expression.count('(') != expression.count(')'):
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message="Unbalanced parentheses in expression",
                context=context,
                suggestion="Ensure every opening parenthesis has a matching closing one"
            ))
        
        # Check for balanced quotes
        single_quotes = expression.count("'") - expression.count("\\'")
        double_quotes = expression.count('"') - expression.count('\\"')
        
        if single_quotes % 2 != 0:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message="Unmatched single quotes in expression",
                context=context,
                suggestion="Ensure all single quotes are properly paired"
            ))
        
        if double_quotes % 2 != 0:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message="Unmatched double quotes in expression",
                context=context,
                suggestion="Ensure all double quotes are properly paired"
            ))
        
        return issues
    
    def _validate_field_references(self, expression: str, context: str,
                                 available_fields: Optional[Set[str]] = None) -> List[ValidationIssue]:
        """Validate field references in expression."""
        issues = []
        
        # Extract field names from expression
        field_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b')
        referenced_fields = set()
        
        for match in field_pattern.finditer(expression):
            field_name = match.group(1)
            # Skip Python keywords and built-in functions
            if field_name not in {'and', 'or', 'not', 'in', 'is', 'True', 'False', 'None',
                                 'len', 'sum', 'max', 'min', 'abs', 'str', 'int', 'float',
                                 'startswith', 'endswith', 'contains'}:
                referenced_fields.add(field_name)
        
        if not referenced_fields:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message="Expression doesn't reference any fields",
                context=context,
                suggestion="Add field references to make the expression dynamic",
                fix_hint="Example: 'amount > 100' instead of 'True'"
            ))
            return issues
        
        # Check against available fields
        if available_fields:
            missing_fields = referenced_fields - available_fields
            if missing_fields:
                # Suggest similar field names
                suggestions = self._suggest_similar_fields(missing_fields, available_fields)
                
                for missing_field in missing_fields:
                    suggestion = suggestions.get(missing_field, "Check your field names")
                    issues.append(ValidationIssue(
                        level=ValidationLevel.WARNING,
                        message=f"Field '{missing_field}' not found in available fields",
                        context=context,
                        field_name=missing_field,
                        suggestion=suggestion,
                        fix_hint="Ensure the field exists in your facts data"
                    ))
        
        return issues
    
    def _detect_common_mistakes(self, expression: str, context: str) -> List[ValidationIssue]:
        """Detect common expression mistakes."""
        issues = []
        
        # Check for assignment instead of comparison
        if '=' in expression and '==' not in expression and '!=' not in expression:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message="Found assignment operator '=' instead of comparison '=='",
                context=context,
                suggestion="Use '==' for equality comparison, '=' is for assignment",
                fix_hint="Change '=' to '==' for comparison"
            ))
        
        # Check for common string comparison mistakes
        if re.search(r'\w+\s*==\s*[^\'"][^\'"\s]*[^\'"]', expression):
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message="Possible unquoted string in comparison",
                context=context,
                suggestion="String literals should be quoted",
                fix_hint="Use 'field == \"value\"' instead of 'field == value'"
            ))
        
        # Check for Java-style string comparison
        if '.equals(' in expression:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message="Java-style .equals() method not supported",
                context=context,
                suggestion="Use '==' for string comparison in Python",
                fix_hint="Change 'field.equals(\"value\")' to 'field == \"value\"'"
            ))
        
        # Check for SQL-style operators
        sql_operators = {'LIKE', 'ILIKE', 'AND', 'OR', 'NOT'}
        expression_upper = expression.upper()
        for op in sql_operators:
            if f' {op} ' in expression_upper:
                python_equivalent = {
                    'LIKE': 'in or startswith/endswith',
                    'AND': 'and',
                    'OR': 'or', 
                    'NOT': 'not'
                }.get(op, op.lower())
                
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"SQL-style operator '{op}' not supported",
                    context=context,
                    suggestion=f"Use Python equivalent: {python_equivalent}",
                    fix_hint=f"Replace '{op}' with '{python_equivalent}'"
                ))
        
        # Check for undefined function calls
        function_pattern = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\(')
        known_functions = {
            'len', 'sum', 'max', 'min', 'abs', 'str', 'int', 'float', 'bool',
            'startswith', 'endswith', 'contains', 'upper', 'lower', 'strip'
        }
        
        for match in function_pattern.finditer(expression):
            func_name = match.group(1)
            if func_name not in known_functions:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    message=f"Unknown function '{func_name}'",
                    context=context,
                    suggestion="Check if the function name is correct",
                    fix_hint=f"Available functions: {', '.join(sorted(known_functions))}"
                ))
        
        return issues
    
    def _check_expression_complexity(self, expression: str, context: str) -> List[ValidationIssue]:
        """Check expression complexity and suggest simplifications."""
        issues = []
        
        # Check length
        if len(expression) > 500:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message=f"Very long expression ({len(expression)} characters)",
                context=context,
                suggestion="Consider breaking into multiple rules or simplifying",
                fix_hint="Long expressions are harder to debug and maintain"
            ))
        
        # Check nesting depth by counting parentheses
        max_depth = 0
        current_depth = 0
        for char in expression:
            if char == '(':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == ')':
                current_depth -= 1
        
        if max_depth > 5:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message=f"Deeply nested expression (depth: {max_depth})",
                context=context,
                suggestion="Consider simplifying or breaking into multiple conditions",
                fix_hint="Deep nesting makes expressions hard to understand"
            ))
        
        # Check for repeated patterns
        words = re.findall(r'\b\w+\b', expression)
        if len(words) > len(set(words)) * 2:  # More than 50% repetition
            issues.append(ValidationIssue(
                level=ValidationLevel.INFO,
                message="Expression has repeated patterns",
                context=context,
                suggestion="Consider if the expression can be simplified",
                fix_hint="Repetitive expressions might benefit from refactoring"
            ))
        
        return issues
    
    def _validate_rule_id(self, rule_id_value: Any, context: str, 
                         line_number: Optional[int] = None) -> List[ValidationIssue]:
        """Validate rule ID."""
        issues = []
        
        if not isinstance(rule_id_value, str):
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Rule ID must be string, got {type(rule_id_value).__name__}",
                context=context,
                line_number=line_number,
                suggestion="Use a string value for rule ID"
            ))
            return issues
        
        if not rule_id_value:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message="Rule ID cannot be empty",
                context=context,
                line_number=line_number,
                suggestion="Provide a descriptive rule ID"
            ))
            return issues
        
        # Check format
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_.-]*$', rule_id_value):
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message=f"Rule ID '{rule_id_value}' has unusual format",
                context=context,
                line_number=line_number,
                suggestion="Use alphanumeric characters, dots, underscores, and hyphens",
                fix_hint="Example: 'customer_validation' or 'tier.premium.check'"
            ))
        
        # Check length
        if len(rule_id_value) > 100:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message=f"Rule ID is very long ({len(rule_id_value)} characters)",
                context=context,
                line_number=line_number,
                suggestion="Use shorter, more concise rule IDs"
            ))
        
        return issues
    
    def _validate_priority(self, priority_value: Any, context: str,
                          line_number: Optional[int] = None) -> List[ValidationIssue]:
        """Validate rule priority."""
        issues = []
        
        if not isinstance(priority_value, (int, float)):
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Priority must be numeric, got {type(priority_value).__name__}",
                context=context,
                line_number=line_number,
                suggestion="Use an integer value for priority (default: 50)"
            ))
            return issues
        
        if priority_value < 0:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Priority cannot be negative: {priority_value}",
                context=context,
                line_number=line_number,
                suggestion="Use non-negative priority values"
            ))
        
        if priority_value > 1000:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message=f"Very high priority: {priority_value}",
                context=context,
                line_number=line_number,
                suggestion="Consider if such high priority is necessary",
                fix_hint="Typical priorities range from 0-100"
            ))
        
        return issues
    
    def _validate_actions(self, actions_data: Any, context: str,
                         line_number: Optional[int] = None) -> List[ValidationIssue]:
        """Validate rule actions."""
        issues = []
        
        if not isinstance(actions_data, dict):
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Actions must be dictionary, got {type(actions_data).__name__}",
                context=context,
                line_number=line_number,
                suggestion="Use dictionary format: {set: {field: value}}",
                fix_hint="Example: then: {set: {status: approved}}"
            ))
            return issues
        
        if not actions_data:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message="Actions dictionary is empty",
                context=context,
                line_number=line_number,
                suggestion="Add actions to make the rule functional",
                fix_hint="Example: then: {set: {result: true}}"
            ))
        
        # Validate 'set' actions
        if 'set' in actions_data:
            set_data = actions_data['set']
            if not isinstance(set_data, dict):
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message="'set' action must be dictionary",
                    context=f"{context}.set",
                    line_number=line_number,
                    suggestion="Use dictionary format: {field: value}",
                    fix_hint="Example: set: {status: approved, priority: high}"
                ))
            elif not set_data:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    message="'set' action is empty",
                    context=f"{context}.set",
                    line_number=line_number,
                    suggestion="Add fields to set when rule fires"
                ))
        
        return issues
    
    def _validate_tags(self, tags_data: Any, context: str,
                      line_number: Optional[int] = None) -> List[ValidationIssue]:
        """Validate rule tags."""
        issues = []
        
        if not isinstance(tags_data, list):
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Tags must be list, got {type(tags_data).__name__}",
                context=context,
                line_number=line_number,
                suggestion="Use list format: [tag1, tag2]",
                fix_hint="Example: tags: [customer, validation, tier]"
            ))
            return issues
        
        for i, tag in enumerate(tags_data):
            if not isinstance(tag, str):
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"Tag at position {i} must be string, got {type(tag).__name__}",
                    context=f"{context}.tags[{i}]",
                    line_number=line_number,
                    suggestion="Use string values for tags"
                ))
            elif not tag:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    message=f"Empty tag at position {i}",
                    context=f"{context}.tags[{i}]",
                    line_number=line_number,
                    suggestion="Remove empty tags or provide meaningful names"
                ))
        
        return issues
    
    def _analyze_cross_rule_patterns(self, rules: List[Dict[str, Any]], 
                                   context: str) -> List[ValidationIssue]:
        """Analyze patterns across multiple rules."""
        issues = []
        
        # Check for rules with same priority
        priority_groups = {}
        for i, rule in enumerate(rules):
            priority_val = rule.get('priority', 50)
            if priority_val not in priority_groups:
                priority_groups[priority_val] = []
            priority_groups[priority_val].append((i, rule.get('id', f'rule_{i}')))
        
        for priority_val, rule_list in priority_groups.items():
            if len(rule_list) > 10:
                rule_ids = [rule_id for _, rule_id in rule_list]
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    message=f"Many rules ({len(rule_list)}) have same priority {priority_val}",
                    context=context,
                    suggestion="Consider using different priorities for better ordering",
                    fix_hint=f"Affected rules: {', '.join(rule_ids[:5])}{'...' if len(rule_ids) > 5 else ''}"
                ))
        
        return issues
    
    def _suggest_similar_fields(self, missing_fields: Set[str], 
                               available_fields: Set[str]) -> Dict[str, str]:
        """Suggest similar field names for missing fields."""
        suggestions = {}
        
        for missing in missing_fields:
            best_match = None
            best_score = 0
            
            for available in available_fields:
                # Simple similarity scoring
                score = self._similarity_score(missing, available)
                if score > best_score and score > 0.6:  # Threshold for similarity
                    best_score = score
                    best_match = available
            
            if best_match:
                suggestions[missing] = f"Did you mean '{best_match}'?"
            else:
                suggestions[missing] = f"Available fields: {', '.join(sorted(available_fields)[:5])}"
        
        return suggestions
    
    def _similarity_score(self, a: str, b: str) -> float:
        """Calculate similarity score between two strings."""
        # Simple Jaccard similarity on character bigrams
        if not a or not b:
            return 0.0
        
        a_bigrams = set(a[i:i+2] for i in range(len(a)-1))
        b_bigrams = set(b[i:i+2] for i in range(len(b)-1))
        
        if not a_bigrams and not b_bigrams:
            return 1.0
        
        intersection = len(a_bigrams & b_bigrams)
        union = len(a_bigrams | b_bigrams)
        
        return intersection / union if union > 0 else 0.0
    
    def _update_field_types(self, facts_data: Dict[str, Any]) -> None:
        """Update field type tracking for better validation."""
        for field_name, value in facts_data.items():
            if field_name not in self._field_types:
                self._field_types[field_name] = set()
            self._field_types[field_name].add(type(value))


# Convenience functions
def validate_facts(facts_data: Any, expected_fields: Optional[Set[str]] = None,
                  strict: bool = False) -> ValidationResult:
    """Validate facts with helpful error messages."""
    validator = EnhancedValidator(strict=strict)
    return validator.validate_facts(facts_data, expected_fields)


def validate_expression(expression: str, available_fields: Optional[Set[str]] = None,
                       context: str = "", strict: bool = False) -> ValidationResult:
    """Validate expression with detailed feedback."""
    validator = EnhancedValidator(strict=strict)
    return validator.validate_expression(expression, context, available_fields)


def validate_rule_dict(rule_data: Dict[str, Any], context: str = "",
                      line_number: Optional[int] = None, strict: bool = False) -> ValidationResult:
    """Validate a rule dictionary."""
    validator = EnhancedValidator(strict=strict)
    return validator.validate_rule(rule_data, context, line_number) 