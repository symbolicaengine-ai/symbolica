"""
Validation Service
==================

Handles rule validation logic including duplicate checking and chaining validation.
Separated from Engine to follow Single Responsibility Principle.
"""

from typing import List, Set, Dict, Any
from ..models import Rule
from ..exceptions import ValidationError


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
        
        # Facts validation (optional field)
        if not isinstance(rule.facts, dict):
            raise ValidationError(f"Rule '{rule.id}' facts must be a dictionary")
        
        # Facts can be empty (optional), but if provided, check for reasonable values
        if rule.facts:
            empty_facts = [key for key, value in rule.facts.items() if value is None]
            if empty_facts and len(empty_facts) == len(rule.facts):
                raise ValidationError(f"Rule '{rule.id}' cannot have all facts set to None")
        
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
        # O(n) duplicate detection - single pass with set tracking
        seen = set()
        duplicates = []
        
        for rule in rules:
            if rule.id in seen:
                duplicates.append(rule.id)
            else:
                seen.add(rule.id)
        
        if duplicates:
            raise ValidationError(f"Duplicate rule IDs found: {duplicates}")
    
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
        """Check for circular dependencies in rule chaining using O(n) algorithm.
        
        Args:
            rules: List of rules to check
            
        Raises:
            ValidationError: If circular dependencies are found
        """
        # Build adjacency list
        graph: Dict[str, List[str]] = {}
        for rule in rules:
            graph[rule.id] = rule.triggers.copy()
        
        # Three-color DFS for cycle detection: O(V + E) = O(n)
        # WHITE = 0 (unvisited), GRAY = 1 (visiting), BLACK = 2 (visited)
        color = {rule.id: 0 for rule in rules}
        
        def dfs(node_id: str) -> bool:
            """DFS with three-color marking for cycle detection."""
            if color[node_id] == 1:  # GRAY - back edge found, cycle detected
                return True
            if color[node_id] == 2:  # BLACK - already processed
                return False
            
            color[node_id] = 1  # Mark as GRAY (visiting)
            
            # Visit all neighbors
            for neighbor in graph.get(node_id, []):
                if neighbor in color and dfs(neighbor):
                    return True
            
            color[node_id] = 2  # Mark as BLACK (visited)
            return False
        
        # Check each unvisited node
        for rule in rules:
            if color[rule.id] == 0:  # WHITE (unvisited)
                if dfs(rule.id):
                    raise ValidationError(
                        f"Circular dependency detected in rule chaining involving rule '{rule.id}'"
                    )
    
    def get_dependency_analysis(self, rules: List[Rule]) -> Dict[str, Any]:
        """Get dependency analysis for rules.
        
        Args:
            rules: List of rules to analyze
            
        Returns:
            Dictionary containing dependency analysis
        """
        if not rules:
            return {
                'total_rules': 0,
                'chaining_rules': 0,
                'max_chain_length': 0,
                'circular_dependencies': []
            }
        
        # Count rules with triggers
        chaining_rules = sum(1 for rule in rules if rule.triggers)
        
        # Find max chain length
        max_chain_length = 0
        for rule in rules:
            chain_length = self._find_chain_length(rule, rules, set())
            max_chain_length = max(max_chain_length, chain_length)
        
        # Check for circular dependencies (non-raising version)
        circular_deps = self._find_circular_dependencies(rules)
        
        return {
            'total_rules': len(rules),
            'chaining_rules': chaining_rules,
            'max_chain_length': max_chain_length,
            'circular_dependencies': circular_deps
        }
    
    def _find_chain_length(self, rule: Rule, all_rules: List[Rule], visited: Set[str]) -> int:
        """Find the maximum chain length starting from a rule."""
        if rule.id in visited:
            return 0  # Circular reference or already counted
        
        if not rule.triggers:
            return 1  # End of chain
        
        visited.add(rule.id)
        max_length = 1
        
        for trigger_id in rule.triggers:
            triggered_rule = next((r for r in all_rules if r.id == trigger_id), None)
            if triggered_rule:
                length = 1 + self._find_chain_length(triggered_rule, all_rules, visited.copy())
                max_length = max(max_length, length)
        
        return max_length
    
    def _find_circular_dependencies(self, rules: List[Rule]) -> List[str]:
        """Find circular dependencies without raising exceptions."""
        circular_deps = []
        
        # Build adjacency list
        graph: Dict[str, List[str]] = {}
        for rule in rules:
            graph[rule.id] = rule.triggers.copy()
        
        # Three-color DFS
        color = {rule.id: 0 for rule in rules}
        
        def dfs(node_id: str, path: List[str]) -> None:
            if color[node_id] == 1:  # GRAY - cycle found
                cycle_start = path.index(node_id)
                cycle = path[cycle_start:] + [node_id]
                circular_deps.append(" -> ".join(cycle))
                return
            if color[node_id] == 2:  # BLACK - already processed
                return
            
            color[node_id] = 1  # Mark as GRAY
            path.append(node_id)
            
            for neighbor in graph.get(node_id, []):
                if neighbor in color:
                    dfs(neighbor, path.copy())
            
            color[node_id] = 2  # Mark as BLACK
        
        for rule in rules:
            if color[rule.id] == 0:
                dfs(rule.id, [])
        
        return circular_deps 