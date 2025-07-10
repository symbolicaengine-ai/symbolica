"""
Backward Chaining - Reverse DAG Search
======================================

Simple reverse search on the rule DAG to find rules that can achieve a goal.
"""

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.models import Rule, Goal, Facts
    from ...core.interfaces import ConditionEvaluator


class BackwardChainer:
    """Simple reverse DAG search to find rules that can achieve a goal."""
    
    def __init__(self, rules: List['Rule'], evaluator: 'ConditionEvaluator'):
        self.rules = rules
        self.evaluator = evaluator
    
    def find_supporting_rules(self, goal: 'Goal') -> List['Rule']:
        """Find rules that could produce the goal's target fields."""
        supporting_rules = []
        
        for rule in self.rules:
            # Check if this rule's actions could achieve the goal
            for goal_field, goal_value in goal.target.items():
                if goal_field in rule.actions and rule.actions[goal_field] == goal_value:
                    supporting_rules.append(rule)
                    break
        
        return supporting_rules
    
    def can_achieve_goal(self, goal: 'Goal', current_facts: 'Facts') -> bool:
        """Test if goal can be achieved with current facts."""
        supporting_rules = self.find_supporting_rules(goal)
        
        if not supporting_rules:
            return False
        
        # Test if any supporting rule would fire
        from ...core.models import ExecutionContext
        temp_context = ExecutionContext(
            original_facts=current_facts,
            enriched_facts=current_facts.data.copy(),
            fired_rules=[]
        )
        
        for rule in supporting_rules:
            try:
                if self.evaluator.evaluate(rule.condition, temp_context):
                    return True
            except (AttributeError, TypeError, ValueError, SyntaxError):
                # Rule evaluation failed - skip this rule
                continue
        
        return False 