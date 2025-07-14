"""
Backward Chaining Strategy
==========================

Goal-oriented rule discovery using backward chaining search.
Finds rules that can achieve specific goals.
"""

from typing import List, Set, Dict, Optional, TYPE_CHECKING
import logging
from ...core.exceptions import EvaluationError

if TYPE_CHECKING:
    from ...core.models import Rule, Goal, Facts
    from ...core.interfaces import ConditionEvaluator


class BackwardChainer:
    """Backward chaining search for goal-oriented rule discovery."""
    
    def __init__(self, rules: List['Rule'], evaluator: 'ConditionEvaluator'):
        """Initialize backward chainer.
        
        Args:
            rules: Available rules for chaining
            evaluator: Condition evaluator for field extraction
        """
        self.rules = rules
        self.evaluator = evaluator
        self.logger = logging.getLogger('symbolica.BackwardChainer')
        
        # Build reverse index for efficient goal-to-rule lookup
        self._build_goal_index()
    
    def _build_goal_index(self) -> None:
        """Build reverse index mapping output fields to rules that produce them."""
        self.goal_index: Dict[str, List['Rule']] = {}
        
        for rule in self.rules:
            # Index actions
            for action_key in rule.actions.keys():
                if action_key not in self.goal_index:
                    self.goal_index[action_key] = []
                self.goal_index[action_key].append(rule)
            
            # Index facts if available
            if hasattr(rule, 'facts') and rule.facts:
                for fact_key in rule.facts.keys():
                    if fact_key not in self.goal_index:
                        self.goal_index[fact_key] = []
                    self.goal_index[fact_key].append(rule)
    
    def find_supporting_rules(self, goal: 'Goal') -> List['Rule']:
        """Find rules that can produce any of the goal's target facts.
        
        Args:
            goal: Goal to achieve
            
        Returns:
            List of rules that can produce any of the goal's target facts
        """
        if not goal.target_facts:
            return []
        
        all_supporting_rules = []
        
        # For each target fact in the goal, find supporting rules
        for field, expected_value in goal.target_facts.items():
            # Direct lookup using goal index
            supporting_rules = self.goal_index.get(field, [])
            
            # Filter by expected value if specified
            if expected_value is not None:
                filtered_rules = []
                for rule in supporting_rules:
                    # Check if rule's action/fact value matches expected value
                    action_value = rule.actions.get(field)
                    fact_value = getattr(rule, 'facts', {}).get(field)
                    
                    if (action_value == expected_value or 
                        fact_value == expected_value):
                        filtered_rules.append(rule)
                
                supporting_rules = filtered_rules
            
            all_supporting_rules.extend(supporting_rules)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_rules = []
        for rule in all_supporting_rules:
            if rule.id not in seen:
                seen.add(rule.id)
                unique_rules.append(rule)
        
        return unique_rules
    
    def can_achieve_goal(self, goal: 'Goal', current_facts: 'Facts') -> bool:
        """Test if goal can be achieved with current facts and available rules.
        
        Args:
            goal: Goal to test
            current_facts: Current fact state
            
        Returns:
            True if goal is achievable, False otherwise
        """
        # Check if all target facts are already satisfied
        all_satisfied = True
        for field, expected_value in goal.target_facts.items():
            if field in current_facts.data:
                current_value = current_facts.data[field]
                if expected_value is None or current_value == expected_value:
                    continue  # This fact is satisfied
                else:
                    all_satisfied = False
                    break
            else:
                all_satisfied = False
                break
        
        if all_satisfied:
            return True
        
        # Find rules that can produce any of the goal's target facts
        supporting_rules = self.find_supporting_rules(goal)
        if not supporting_rules:
            return False
        
        # Check if any supporting rule can fire with current facts
        for rule in supporting_rules:
            if self._can_rule_fire(rule, current_facts):
                return True
        
        # Check if goal can be achieved through multi-step chaining
        return self._can_achieve_through_chaining(goal, current_facts, set())
    
    def _can_rule_fire(self, rule: 'Rule', current_facts: 'Facts') -> bool:
        """Check if a rule can fire with current facts.
        
        Args:
            rule: Rule to test
            current_facts: Current fact state
            
        Returns:
            True if rule can fire, False otherwise
        """
        try:
            # Create a temporary execution context
            from ...core.models import ExecutionContext
            temp_context = ExecutionContext(
                original_facts=current_facts,
                enriched_facts={},
                fired_rules=[]
            )
            
            # Try to evaluate the rule condition
            result = self.evaluator.evaluate(rule.condition, temp_context)
            return bool(result)
            
        except (EvaluationError, Exception) as e:
            self.logger.warning(f"Failed to evaluate rule {rule.id}: {e}")
            return False
    
    def _can_achieve_through_chaining(self, goal: 'Goal', current_facts: 'Facts', 
                                    visited_goals: Set[str], max_depth: int = 5) -> bool:
        """Check if goal can be achieved through multi-step rule chaining.
        
        Args:
            goal: Goal to achieve
            current_facts: Current fact state
            visited_goals: Set of goals already explored (cycle prevention)
            max_depth: Maximum chaining depth
            
        Returns:
            True if goal can be achieved through chaining, False otherwise
        """
        if max_depth <= 0:
            return False
        
        # Create a goal identifier for cycle prevention
        goal_id = str(sorted(goal.target_facts.items()))
        if goal_id in visited_goals:
            return False
        
        visited_goals.add(goal_id)
        
        # Find rules that can produce any of the target facts
        supporting_rules = self.find_supporting_rules(goal)
        
        for rule in supporting_rules:
            # Get fields required by this rule
            required_fields = self._get_required_fields(rule)
            
            if not required_fields:
                # No prerequisites - if rule can fire, goal is achievable
                if self._can_rule_fire(rule, current_facts):
                    visited_goals.discard(goal_id)
                    return True
                continue
            
            # Check if we can achieve all required fields
            can_achieve_all = True
            for field in required_fields:
                if field in current_facts.data:
                    continue  # Already have this field
                
                # Create subgoal for this field
                subgoal = self._create_subgoal(field)
                
                # Recursively check if subgoal can be achieved
                if not self._can_achieve_through_chaining(subgoal, current_facts, 
                                                        visited_goals.copy(), max_depth - 1):
                    can_achieve_all = False
                    break
            
            if can_achieve_all:
                visited_goals.discard(goal_id)
                return True
        
        visited_goals.discard(goal_id)
        return False
    
    def _get_required_fields(self, rule: 'Rule') -> Set[str]:
        """Get fields required by a rule (from its condition).
        
        Args:
            rule: Rule to analyze
            
        Returns:
            Set of required field names
        """
        try:
            if hasattr(self.evaluator, 'extract_fields'):
                return self.evaluator.extract_fields(rule.condition)
            else:
                # Fallback to empty set if extraction not available
                return set()
        except Exception as e:
            self.logger.warning(f"Failed to extract required fields for rule {rule.id}: {e}")
            return set()
    
    def _create_subgoal(self, field: str) -> 'Goal':
        """Create a subgoal for a required field.
        
        Args:
            field: Field name to create goal for
            
        Returns:
            Goal for the field
        """
        from ...core.models import Goal
        return Goal(target_facts={field: None})  # None means any value
    
    def get_chaining_analysis(self, goal: 'Goal') -> Dict[str, any]:
        """Get analysis of chaining possibilities for a goal.
        
        Args:
            goal: Goal to analyze
            
        Returns:
            Dictionary with chaining analysis
        """
        supporting_rules = self.find_supporting_rules(goal)
        
        analysis = {
            'target_facts': goal.target_facts,
            'direct_supporting_rules': len(supporting_rules),
            'supporting_rule_ids': [rule.id for rule in supporting_rules],
            'chaining_depth': 0,
            'total_rules_in_chain': len(supporting_rules)
        }
        
        # Calculate potential chaining depth
        if supporting_rules:
            max_depth = 0
            for rule in supporting_rules:
                depth = self._calculate_rule_depth(rule, set())
                max_depth = max(max_depth, depth)
            analysis['chaining_depth'] = max_depth
        
        return analysis
    
    def _calculate_rule_depth(self, rule: 'Rule', visited: Set[str]) -> int:
        """Calculate the maximum depth of a rule's dependency chain.
        
        Args:
            rule: Rule to analyze
            visited: Set of rule IDs already visited (cycle prevention)
            
        Returns:
            Maximum depth
        """
        if rule.id in visited:
            return 0  # Prevent infinite recursion
        
        visited.add(rule.id)
        required_fields = self._get_required_fields(rule)
        
        if not required_fields:
            visited.discard(rule.id)
            return 1  # Leaf rule
        
        max_sub_depth = 0
        for field in required_fields:
            supporting_rules = self.goal_index.get(field, [])
            for sub_rule in supporting_rules:
                sub_depth = self._calculate_rule_depth(sub_rule, visited.copy())
                max_sub_depth = max(max_sub_depth, sub_depth)
        
        visited.discard(rule.id)
        return max_sub_depth + 1 