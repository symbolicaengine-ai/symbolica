"""
Validation Service
==================

Handles rule validation logic including duplicate checking and chaining validation.
Separated from Engine to follow Single Responsibility Principle.
"""

from typing import List, Set, Dict
from .models import Rule
from .exceptions import ValidationError


class ValidationService:
    """Handles validation of rules and rule sets."""
    
    def validate_rules(self, rules: List[Rule]) -> None:
        """Validate a list of rules for consistency and correctness.
        
        Args:
            rules: List of rules to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if not rules:
            return  # Empty rule list is valid
        
        # Validate individual rules
        for rule in rules:
            self._validate_single_rule(rule)
        
        # Validate rule set consistency
        self._validate_unique_ids(rules)
        self._validate_rule_chaining(rules)
    
    def _validate_single_rule(self, rule: Rule) -> None:
        """Validate a single rule for correctness.
        
        Args:
            rule: Rule to validate
            
        Raises:
            ValidationError: If rule is invalid
        """
        # ID validation
        if not rule.id or not isinstance(rule.id, str):
            raise ValidationError("Rule ID must be a non-empty string")
        
        if not rule.id.strip():
            raise ValidationError("Rule ID cannot be just whitespace")
        
        # Priority validation
        if not isinstance(rule.priority, int):
            raise ValidationError(f"Rule '{rule.id}' priority must be an integer")
        
        # Condition validation
        if not rule.condition or not isinstance(rule.condition, str):
            raise ValidationError(f"Rule '{rule.id}' must have a non-empty string condition")
        
        if not rule.condition.strip():
            raise ValidationError(f"Rule '{rule.id}' condition cannot be just whitespace")
        
        # Actions validation
        if not rule.actions or not isinstance(rule.actions, dict):
            raise ValidationError(f"Rule '{rule.id}' must have non-empty actions dictionary")
        
        # Check for empty action values (which might be intentional but worth flagging)
        empty_actions = [key for key, value in rule.actions.items() if value is None]
        if empty_actions and len(empty_actions) == len(rule.actions):
            raise ValidationError(f"Rule '{rule.id}' cannot have all actions set to None")
        
        # Tags validation
        if not isinstance(rule.tags, list):
            raise ValidationError(f"Rule '{rule.id}' tags must be a list")
        
        # Validate tag content
        for tag in rule.tags:
            if not isinstance(tag, str):
                raise ValidationError(f"Rule '{rule.id}' tags must be strings")
        
        # Triggers validation
        if not isinstance(rule.triggers, list):
            raise ValidationError(f"Rule '{rule.id}' triggers must be a list")
        
        # Validate trigger content
        for trigger in rule.triggers:
            if not isinstance(trigger, str):
                raise ValidationError(f"Rule '{rule.id}' triggers must be strings")
            if not trigger.strip():
                raise ValidationError(f"Rule '{rule.id}' cannot have empty trigger")
    
    def _validate_unique_ids(self, rules: List[Rule]) -> None:
        """Validate that all rule IDs are unique.
        
        Args:
            rules: List of rules to validate
            
        Raises:
            ValidationError: If duplicate IDs are found
        """
        rule_ids = [rule.id for rule in rules]
        unique_ids = set(rule_ids)
        
        if len(rule_ids) != len(unique_ids):
            # Find duplicates
            seen = set()
            duplicates = set()
            for rule_id in rule_ids:
                if rule_id in seen:
                    duplicates.add(rule_id)
                seen.add(rule_id)
            
            raise ValidationError(f"Duplicate rule IDs found: {list(duplicates)}")
    
    def _validate_rule_chaining(self, rules: List[Rule]) -> None:
        """Validate rule chaining to prevent circular dependencies and ensure targets exist.
        
        Args:
            rules: List of rules to validate
            
        Raises:
            ValidationError: If chaining is invalid
        """
        rule_ids = {rule.id for rule in rules}
        
        # Check that all triggered rules exist
        for rule in rules:
            for triggered_id in rule.triggers:
                if triggered_id not in rule_ids:
                    raise ValidationError(f"Rule '{rule.id}' triggers unknown rule '{triggered_id}'")
        
        # Check for self-triggering
        for rule in rules:
            if rule.id in rule.triggers:
                raise ValidationError(f"Rule '{rule.id}' cannot trigger itself")
        
        # Check for circular dependencies using DFS
        self._check_circular_dependencies(rules)
    
    def _check_circular_dependencies(self, rules: List[Rule]) -> None:
        """Check for circular dependencies in rule chaining.
        
        Args:
            rules: List of rules to check
            
        Raises:
            ValidationError: If circular dependencies are found
        """
        # Build adjacency list for easier traversal
        graph: Dict[str, List[str]] = {}
        for rule in rules:
            graph[rule.id] = rule.triggers.copy()
        
        def has_cycle(start_rule_id: str, visited: Set[str], path: Set[str]) -> bool:
            """DFS to detect cycles."""
            if start_rule_id in path:
                return True
            if start_rule_id in visited:
                return False
            
            visited.add(start_rule_id)
            path.add(start_rule_id)
            
            # Check all rules that this rule triggers
            for triggered_id in graph.get(start_rule_id, []):
                if has_cycle(triggered_id, visited, path):
                    return True
            
            path.remove(start_rule_id)
            return False
        
        visited = set()
        for rule in rules:
            if rule.id not in visited:
                if has_cycle(rule.id, visited, set()):
                    raise ValidationError(
                        f"Circular dependency detected in rule chaining involving rule '{rule.id}'"
                    )
    
    def get_dependency_analysis(self, rules: List[Rule]) -> Dict[str, any]:
        """Analyze rule dependencies and provide statistics.
        
        Args:
            rules: List of rules to analyze
            
        Returns:
            Dictionary with dependency analysis
        """
        if not rules:
            return {
                'total_rules': 0,
                'rules_with_triggers': 0,
                'total_trigger_relationships': 0,
                'max_trigger_depth': 0,
                'isolated_rules': 0
            }
        
        # Build trigger graph
        trigger_graph = {}
        reverse_graph = {}  # Who triggers this rule
        
        for rule in rules:
            trigger_graph[rule.id] = rule.triggers.copy()
            reverse_graph[rule.id] = []
        
        for rule in rules:
            for triggered_id in rule.triggers:
                if triggered_id in reverse_graph:
                    reverse_graph[triggered_id].append(rule.id)
        
        # Calculate statistics
        rules_with_triggers = sum(1 for rule in rules if rule.triggers)
        total_relationships = sum(len(rule.triggers) for rule in rules)
        
        # Find isolated rules (neither trigger nor are triggered)
        isolated_rules = []
        for rule in rules:
            if not rule.triggers and not reverse_graph[rule.id]:
                isolated_rules.append(rule.id)
        
        # Calculate max trigger depth
        max_depth = 0
        for rule_id in trigger_graph:
            depth = self._calculate_trigger_depth(rule_id, trigger_graph, set())
            max_depth = max(max_depth, depth)
        
        return {
            'total_rules': len(rules),
            'rules_with_triggers': rules_with_triggers,
            'total_trigger_relationships': total_relationships,
            'max_trigger_depth': max_depth,
            'isolated_rules': len(isolated_rules),
            'isolated_rule_ids': isolated_rules
        }
    
    def _calculate_trigger_depth(self, rule_id: str, graph: Dict[str, List[str]], visited: Set[str]) -> int:
        """Calculate maximum trigger depth from a rule.
        
        Args:
            rule_id: Starting rule ID
            graph: Trigger graph
            visited: Set of visited rules (to prevent infinite loops)
            
        Returns:
            Maximum depth
        """
        if rule_id in visited:
            return 0  # Prevent infinite loops
        
        if not graph.get(rule_id):
            return 0  # No triggers
        
        visited.add(rule_id)
        max_depth = 0
        
        for triggered_id in graph[rule_id]:
            depth = 1 + self._calculate_trigger_depth(triggered_id, graph, visited.copy())
            max_depth = max(max_depth, depth)
        
        return max_depth 