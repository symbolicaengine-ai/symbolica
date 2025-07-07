"""
DAG-Based Rule Execution Strategy
=================================

Dependency-aware rule execution using topological sort.
Optimized for large rule sets with complex dependencies.
"""

from typing import Dict, List, Set, Optional, Any, TYPE_CHECKING
from collections import defaultdict, deque

from ..core.interfaces import ExecutionStrategy

if TYPE_CHECKING:
    from ..core.models import Rule, ExecutionContext
    from ..core.interfaces import ConditionEvaluator


class DAGStrategy(ExecutionStrategy):
    """
    DAG-based execution strategy with dependency resolution.
    
    Uses topological sorting to execute rules in dependency order,
    ensuring that rules which set facts are executed before rules
    that depend on those facts.
    """
    
    def __init__(self, evaluator: Optional['ConditionEvaluator'] = None):
        self.evaluator = evaluator
        self._dependency_cache: Dict[str, Set[str]] = {}
    
    def get_execution_order(self, rules: List['Rule']) -> List['Rule']:
        """Get rules in dependency-aware execution order."""
        # Build dependency graph
        graph = self._build_dependency_graph(rules)
        
        # Perform topological sort
        return self._topological_sort(rules, graph)
    
    def _build_dependency_graph(self, rules: List['Rule']) -> Dict[str, Set[str]]:
        """Build dependency graph from rules."""
        graph = defaultdict(set)
        
        # Create mapping from rule ID to rule
        rule_map = {rule.id: rule for rule in rules}
        
        for rule in rules:
            # Get fields this rule depends on
            depends_on = self._get_rule_dependencies(rule)
            
            # Find rules that provide these fields
            for other_rule in rules:
                if other_rule.id == rule.id:
                    continue
                
                # Check if other rule provides fields this rule depends on
                provides = set(other_rule.actions.keys())
                if depends_on & provides:
                    graph[rule.id].add(other_rule.id)
        
        return graph
    
    def _get_rule_dependencies(self, rule: 'Rule') -> Set[str]:
        """Get field dependencies for a rule."""
        if rule.id in self._dependency_cache:
            return self._dependency_cache[rule.id]
        
        try:
            if self.evaluator:
                fields = self.evaluator.extract_fields(rule.condition)
                self._dependency_cache[rule.id] = fields
                return fields
        except:
            pass
        
        # Fallback to empty set if no evaluator or extraction fails
        self._dependency_cache[rule.id] = set()
        return set()
    
    def _topological_sort(self, rules: List['Rule'], graph: Dict[str, Set[str]]) -> List['Rule']:
        """Perform topological sort on rules."""
        rule_map = {rule.id: rule for rule in rules}
        
        # Calculate in-degrees
        in_degree = {rule.id: 0 for rule in rules}
        for rule_id in graph:
            for dependency in graph[rule_id]:
                in_degree[rule_id] += 1
        
        # Sort by priority within each level
        queue = deque(sorted(
            [rule for rule in rules if in_degree[rule.id] == 0],
            key=lambda r: r.priority
        ))
        
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            # Remove current rule and update in-degrees
            rules_to_update = []
            for rule_id in graph:
                if current.id in graph[rule_id]:
                    graph[rule_id].remove(current.id)
                    in_degree[rule_id] -= 1
                    if in_degree[rule_id] == 0:
                        rules_to_update.append(rule_map[rule_id])
            
            # Add newly available rules to queue, sorted by priority
            for rule in sorted(rules_to_update, key=lambda r: r.priority):
                queue.append(rule)
        
        # Check for cycles
        if len(result) != len(rules):
            # Fall back to priority-based sorting
            remaining = [rule for rule in rules if rule not in result]
            result.extend(sorted(remaining, key=lambda r: r.priority))
        
        return result
    
 