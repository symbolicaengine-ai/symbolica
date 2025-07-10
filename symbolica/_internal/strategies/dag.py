"""
DAG-Based Rule Execution Strategy
=================================

Dependency-aware rule execution using topological sort.
Optimized for large rule sets with complex dependencies.
"""

from typing import Dict, List, Set, Optional, Any, TYPE_CHECKING
from collections import defaultdict, deque
import logging

from ...core.interfaces import ExecutionStrategy
from ...core.infrastructure.exceptions import DAGError, EvaluationError

if TYPE_CHECKING:
    from ...core.models import Rule, ExecutionContext
    from ...core.interfaces import ConditionEvaluator


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
        self.logger = logging.getLogger('symbolica.DAGStrategy')
    
    def get_execution_order(self, rules: List['Rule']) -> List['Rule']:
        """Get rules in dependency-aware execution order."""
        # Build dependency graph
        graph = self._build_dependency_graph(rules)
        
        # Perform topological sort
        return self._topological_sort(rules, graph)
    
    def _build_dependency_graph(self, rules: List['Rule']) -> Dict[str, Set[str]]:
        """Build dependency graph from rules including field dependencies and rule chaining."""
        graph = defaultdict(set)
        
        # Create mapping from rule ID to rule and collect what facts each rule produces
        rule_map = {rule.id: rule for rule in rules}
        rule_produces = {}  # rule_id -> set of fact names it produces
        rule_consumes = {}  # rule_id -> set of fact names it consumes
        
        # Analyze what each rule produces and consumes
        for rule in rules:
            # Facts this rule produces (from actions)
            produces = set(rule.actions.keys()) if rule.actions else set()
            rule_produces[rule.id] = produces
            
            # Facts this rule consumes (from condition fields)
            try:
                consumes = self._get_rule_dependencies(rule)
                rule_consumes[rule.id] = consumes
            except (AttributeError, TypeError, ValueError, EvaluationError) as e:
                # Log field extraction failure and assume no dependencies
                self.logger.warning(
                    f"Failed to extract dependencies for rule '{rule.id}': {str(e)}",
                    extra={'rule_id': rule.id, 'condition': rule.condition}
                )
                rule_consumes[rule.id] = set()
        
        # Build field-based dependencies: if rule A produces fact X and rule B consumes fact X,
        # then rule B depends on rule A
        for consumer_id, consumed_facts in rule_consumes.items():
            for producer_id, produced_facts in rule_produces.items():
                if consumer_id != producer_id:  # Don't create self-dependencies
                    # If consumer needs any fact that producer creates
                    if consumed_facts & produced_facts:
                        graph[consumer_id].add(producer_id)
        
        # Add explicit rule chaining dependencies
        for rule in rules:
            for triggered_rule_id in getattr(rule, 'triggers', []):
                if triggered_rule_id in rule_map:
                    # Triggered rule depends on the triggering rule
                    graph[triggered_rule_id].add(rule.id)
        
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
        except (AttributeError, TypeError, ValueError, SyntaxError, EvaluationError) as e:
            # Log field extraction failure and fall back to empty set
            self.logger.debug(
                f"Field extraction failed for rule '{rule.id}': {str(e)}",
                extra={'rule_id': rule.id, 'condition': rule.condition}
            )
        
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
        
        # Sort by priority within each level (higher priority first)
        queue = deque(sorted(
            [rule for rule in rules if in_degree[rule.id] == 0],
            key=lambda r: r.priority,
            reverse=True
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
            
            # Add newly available rules to queue, sorted by priority (higher priority first)
            for rule in sorted(rules_to_update, key=lambda r: r.priority, reverse=True):
                queue.append(rule)
        
        # Check for cycles
        if len(result) != len(rules):
            remaining = [rule for rule in rules if rule not in result]
            remaining_ids = [rule.id for rule in remaining]
            
            # Log the cycle detection
            self.logger.warning(
                f"Circular dependencies detected in rules: {remaining_ids}. Using priority fallback.",
                extra={'cycle_rules': remaining_ids, 'completed_rules': len(result)}
            )
            
            # Fall back to priority-based sorting (higher priority first)
            result.extend(sorted(remaining, key=lambda r: r.priority, reverse=True))
        
        return result
    
 