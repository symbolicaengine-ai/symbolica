"""
Rule Validator
=============

Comprehensive validation for rules and rule sets.

Features:
- Expression validation
- Dependency validation
- Performance analysis
- Best practice checks
"""

from typing import List, Dict, Any, Set, Tuple, Union
from collections import defaultdict

from ..core import Rule, RuleSet, ValidationError
from .._internal.evaluator import create_evaluator


class RuleValidator:
    """
    Comprehensive rule validator.
    
    Features:
    - Expression syntax validation
    - Semantic validation
    - Dependency conflict detection
    - Performance issue identification
    - Best practice enforcement
    """
    
    def __init__(self, strict: bool = False):
        self.strict = strict
        self.evaluator = create_evaluator()
    
    def validate_rule(self, rule: Rule) -> Dict[str, Any]:
        """Validate a single rule."""
        errors = []
        warnings = []
        
        # Validate rule ID
        id_validation = self._validate_rule_id(rule)
        errors.extend(id_validation.get('errors', []))
        warnings.extend(id_validation.get('warnings', []))
        
        # Validate priority
        priority_validation = self._validate_priority(rule)
        errors.extend(priority_validation.get('errors', []))
        warnings.extend(priority_validation.get('warnings', []))
        
        # Validate condition
        condition_validation = self._validate_condition(rule)
        errors.extend(condition_validation.get('errors', []))
        warnings.extend(condition_validation.get('warnings', []))
        
        # Validate actions
        actions_validation = self._validate_actions(rule)
        errors.extend(actions_validation.get('errors', []))
        warnings.extend(actions_validation.get('warnings', []))
        
        # Validate tags
        tags_validation = self._validate_tags(rule)
        errors.extend(tags_validation.get('errors', []))
        warnings.extend(tags_validation.get('warnings', []))
        
        return {
            'rule_id': rule.id.value,
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def validate_rule_set(self, rule_set: RuleSet) -> Dict[str, Any]:
        """Validate an entire rule set."""
        errors = []
        warnings = []
        rule_validations = []
        
        # Validate individual rules
        for rule in rule_set.rules:
            validation = self.validate_rule(rule)
            rule_validations.append(validation)
            errors.extend(validation['errors'])
            warnings.extend(validation['warnings'])
        
        # Cross-rule validations
        cross_validation = self._validate_cross_rule_issues(rule_set.rules)
        errors.extend(cross_validation.get('errors', []))
        warnings.extend(cross_validation.get('warnings', []))
        
        # Performance analysis
        performance_analysis = self._analyze_performance_issues(rule_set.rules)
        warnings.extend(performance_analysis.get('warnings', []))
        
        return {
            'valid': len(errors) == 0,
            'total_rules': rule_set.rule_count,
            'valid_rules': sum(1 for rv in rule_validations if rv['valid']),
            'errors': errors,
            'warnings': warnings,
            'rule_validations': rule_validations,
            'performance_analysis': performance_analysis
        }
    
    def _validate_rule_id(self, rule: Rule) -> Dict[str, Any]:
        """Validate rule ID."""
        errors = []
        warnings = []
        
        rule_id = rule.id.value
        
        # Check format
        if not rule_id:
            errors.append("Rule ID cannot be empty")
        elif len(rule_id) > 100:
            warnings.append(f"Rule ID is very long ({len(rule_id)} chars)")
        
        # Check for best practices
        if ' ' in rule_id:
            warnings.append("Rule ID contains spaces - consider using underscores or dots")
        
        if rule_id.upper() == rule_id:
            warnings.append("Rule ID is all uppercase - consider using lowercase with separators")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_priority(self, rule: Rule) -> Dict[str, Any]:
        """Validate rule priority."""
        errors = []
        warnings = []
        
        priority_value = rule.priority.value
        
        # Check range
        if priority_value < 0:
            errors.append(f"Priority cannot be negative: {priority_value}")
        elif priority_value > 1000:
            warnings.append(f"Very high priority ({priority_value}) - ensure this is intentional")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_condition(self, rule: Rule) -> Dict[str, Any]:
        """Validate rule condition."""
        errors = []
        warnings = []
        
        try:
            # Try to extract fields (validates expression syntax)
            fields = self.evaluator.extract_fields(rule.condition)
            
            # Check for common issues
            expression = rule.condition.expression
            
            # Check expression length
            if len(expression) > 500:
                warnings.append(f"Very long expression ({len(expression)} chars) - consider simplifying")
            
            # Check for potential issues
            if 'and and' in expression or 'or or' in expression:
                warnings.append("Possible duplicate boolean operators in expression")
            
            if expression.count('(') != expression.count(')'):
                errors.append("Unmatched parentheses in expression")
            
            # Check field usage
            if not fields:
                warnings.append("Expression doesn't reference any fields - will evaluate to constant")
            elif len(fields) > 20:
                warnings.append(f"Expression references many fields ({len(fields)}) - may impact performance")
            
        except Exception as e:
            errors.append(f"Invalid expression syntax: {e}")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_actions(self, rule: Rule) -> Dict[str, Any]:
        """Validate rule actions."""
        errors = []
        warnings = []
        
        if not rule.actions:
            errors.append("Rule must have at least one action")
            return {'errors': errors, 'warnings': warnings}
        
        # Check each action
        for i, action in enumerate(rule.actions):
            # Validate action type
            if not action.type:
                errors.append(f"Action {i} has empty type")
                continue
            
            # Validate parameters
            if not isinstance(action.parameters, dict):
                errors.append(f"Action {i} parameters must be a dictionary")
                continue
            
            # Check for specific action types
            if action.type == 'set':
                if not action.parameters:
                    warnings.append(f"Set action {i} has no parameters - will do nothing")
                
                # Check for field overwrites
                set_fields = set(action.parameters.keys())
                if len(set_fields) > 10:
                    warnings.append(f"Set action {i} sets many fields ({len(set_fields)}) - consider splitting")
            
            elif action.type == 'call':
                if 'function' not in action.parameters:
                    errors.append(f"Call action {i} missing 'function' parameter")
        
        # Check for duplicate actions
        action_signatures = []
        for action in rule.actions:
            signature = (action.type, frozenset(action.parameters.items()))
            if signature in action_signatures:
                warnings.append("Rule has duplicate actions")
            action_signatures.append(signature)
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_tags(self, rule: Rule) -> Dict[str, Any]:
        """Validate rule tags."""
        errors = []
        warnings = []
        
        if len(rule.tags) > 20:
            warnings.append(f"Rule has many tags ({len(rule.tags)}) - consider reducing")
        
        for tag in rule.tags:
            if not isinstance(tag, str):
                errors.append(f"Tag must be string, got {type(tag)}")
            elif len(tag) > 50:
                warnings.append(f"Very long tag: {tag}")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_cross_rule_issues(self, rules: List[Rule]) -> Dict[str, Any]:
        """Validate issues across multiple rules."""
        errors = []
        warnings = []
        
        # Check for duplicate rule IDs
        rule_ids = [rule.id.value for rule in rules]
        duplicate_ids = {id for id in rule_ids if rule_ids.count(id) > 1}
        for dup_id in duplicate_ids:
            errors.append(f"Duplicate rule ID: {dup_id}")
        
        # Check for field conflicts
        field_conflicts = self._detect_field_conflicts(rules)
        for conflict in field_conflicts:
            warnings.append(f"Field '{conflict['field']}' written by multiple rules: {conflict['rules']}")
        
        # Check for unreachable rules
        unreachable = self._find_unreachable_rules(rules)
        for rule_id in unreachable:
            warnings.append(f"Rule '{rule_id}' may be unreachable due to higher priority rules")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _detect_field_conflicts(self, rules: List[Rule]) -> List[Dict[str, Any]]:
        """Detect fields written by multiple rules."""
        field_writers = defaultdict(list)
        
        for rule in rules:
            for field in rule.written_fields:
                field_writers[field].append(rule.id.value)
        
        conflicts = []
        for field, writers in field_writers.items():
            if len(writers) > 1:
                # Check if they have different priorities
                rule_priorities = {}
                for rule in rules:
                    if rule.id.value in writers:
                        rule_priorities[rule.id.value] = rule.priority.value
                
                unique_priorities = len(set(rule_priorities.values()))
                if unique_priorities == 1:
                    # Same priority - real conflict
                    conflicts.append({
                        'field': field,
                        'rules': writers,
                        'severity': 'high'
                    })
                else:
                    # Different priorities - resolvable
                    conflicts.append({
                        'field': field,
                        'rules': writers,
                        'severity': 'low'
                    })
        
        return conflicts
    
    def _find_unreachable_rules(self, rules: List[Rule]) -> List[str]:
        """Find rules that may be unreachable due to priority ordering."""
        # This is a simplified check - would need more sophisticated analysis
        # for complex dependency scenarios
        
        # Sort by priority
        sorted_rules = sorted(rules, key=lambda r: r.priority.value, reverse=True)
        
        unreachable = []
        processed_fields = set()
        
        for rule in sorted_rules:
            # Check if this rule's written fields are already written by higher priority rules
            written_fields = rule.written_fields
            overlapping = written_fields & processed_fields
            
            if overlapping and len(overlapping) == len(written_fields):
                # All fields this rule writes are already written by higher priority rules
                unreachable.append(rule.id.value)
            
            processed_fields.update(written_fields)
        
        return unreachable
    
    def _analyze_performance_issues(self, rules: List[Rule]) -> Dict[str, Any]:
        """Analyze potential performance issues."""
        warnings = []
        
        # Check for many rules with same priority
        priority_counts = defaultdict(int)
        for rule in rules:
            priority_counts[rule.priority.value] += 1
        
        for priority, count in priority_counts.items():
            if count > 20:
                warnings.append(f"Many rules ({count}) have same priority {priority} - may impact ordering")
        
        # Check for complex expressions
        complex_rules = []
        for rule in rules:
            expression_length = len(rule.condition.expression)
            field_count = len(self.evaluator.extract_fields(rule.condition))
            
            if expression_length > 200 or field_count > 15:
                complex_rules.append(rule.id.value)
        
        if complex_rules:
            warnings.append(f"Rules with complex expressions: {complex_rules}")
        
        # Check for many actions per rule
        heavy_rules = []
        for rule in rules:
            if len(rule.actions) > 10:
                heavy_rules.append(rule.id.value)
        
        if heavy_rules:
            warnings.append(f"Rules with many actions: {heavy_rules}")
        
        return {'warnings': warnings}


# Convenience function
def validate_rules(rules_or_rule_set: Union[List[Rule], RuleSet], 
                  strict: bool = False) -> Dict[str, Any]:
    """Validate rules or rule set."""
    validator = RuleValidator(strict=strict)
    
    if isinstance(rules_or_rule_set, RuleSet):
        return validator.validate_rule_set(rules_or_rule_set)
    else:
        # Create temporary rule set
        rule_set = RuleSet(rules_or_rule_set)
        return validator.validate_rule_set(rule_set) 