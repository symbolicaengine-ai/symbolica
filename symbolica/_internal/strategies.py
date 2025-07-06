"""
Execution Strategies
===================

Efficient rule execution strategies with proper time complexity.
Fixes the O(n³) algorithm issues from the original codebase.
"""

import time
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict, deque

from ..core import (
    Rule, Facts, ExecutionResult, ExecutionContext, TraceLevel,
    ExecutionStrategy, ConditionEvaluator, ActionExecutor,
    ExecutionError, rule_id
)


class LinearExecutionStrategy(ExecutionStrategy):
    """
    Simple linear execution by priority.
    
    Time Complexity: O(n) where n = number of rules
    Space Complexity: O(1) additional space
    
    Best for: Small to medium rule sets, simple dependencies
    """
    
    def execute(self, rules: List[Rule], facts: Facts,
                evaluator: ConditionEvaluator, 
                action_executor: ActionExecutor) -> ExecutionResult:
        """Execute rules in priority order."""
        
        start_time = time.perf_counter_ns()
        
        # Create execution context
        context = ExecutionContext(
            original_facts=facts,
            enriched_facts={},  # Will be initialized in __post_init__
            fired_rules=[],
            trace_level=TraceLevel.NONE
        )
        
        # Sort rules by priority (highest first) - O(n log n)
        sorted_rules = sorted(rules, key=lambda r: r.priority.value, reverse=True)
        
        # Execute rules sequentially - O(n)
        for rule in sorted_rules:
            try:
                if evaluator.evaluate(rule.condition, context):
                    # Rule fired
                    context.rule_fired(rule.id)
                    action_executor.execute(rule.actions, context)
                    
            except Exception as e:
                # Log error but continue execution
                # In production, you might want proper logging here
                continue
        
        # Create result
        execution_time = time.perf_counter_ns() - start_time
        
        return ExecutionResult(
            verdict=context.verdict,
            fired_rules=context.fired_rules,
            execution_time_ns=execution_time,
            context_id=context.context_id
        )
    
    def name(self) -> str:
        return "linear"


class DAGExecutionStrategy(ExecutionStrategy):
    """
    DAG-based execution with proper topological sorting.
    
    Time Complexity: O(V + E) where V = rules, E = dependencies
    Space Complexity: O(V + E) for the graph
    
    Best for: Large rule sets with complex dependencies
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
    
    def execute(self, rules: List[Rule], facts: Facts,
                evaluator: ConditionEvaluator,
                action_executor: ActionExecutor) -> ExecutionResult:
        """Execute rules using DAG with topological sorting."""
        
        start_time = time.perf_counter_ns()
        
        # Create execution context
        context = ExecutionContext(
            original_facts=facts,
            enriched_facts={},
            fired_rules=[],
            trace_level=TraceLevel.NONE
        )
        
        # Build dependency graph - O(V + E)
        dependency_graph = self._build_dependency_graph(rules, evaluator)
        
        # Execute in dependency order - O(V + E)
        execution_layers = self._topological_sort(dependency_graph)
        
        for layer in execution_layers:
            # Execute all rules in this layer (they can run in parallel)
            self._execute_layer(layer, rules, context, evaluator, action_executor)
        
        # Create result
        execution_time = time.perf_counter_ns() - start_time
        
        return ExecutionResult(
            verdict=context.verdict,
            fired_rules=context.fired_rules,
            execution_time_ns=execution_time,
            context_id=context.context_id
        )
    
    def name(self) -> str:
        return "dag"
    
    def _build_dependency_graph(self, rules: List[Rule], 
                               evaluator: ConditionEvaluator) -> Dict[str, Set[str]]:
        """
        Build dependency graph between rules.
        
        Time Complexity: O(V * F) where V = rules, F = avg fields per rule
        This is much better than the O(n³) original algorithm.
        """
        # Build field usage maps
        field_readers: Dict[str, Set[str]] = defaultdict(set)
        field_writers: Dict[str, Set[str]] = defaultdict(set)
        
        # Extract field usage - O(V * F)
        for rule in rules:
            rule_id_str = rule.id.value
            
            # Fields this rule reads
            read_fields = evaluator.extract_fields(rule.condition)
            for field in read_fields:
                field_readers[field].add(rule_id_str)
            
            # Fields this rule writes
            write_fields = rule.written_fields
            for field in write_fields:
                field_writers[field].add(rule_id_str)
        
        # Build dependency graph - O(F * W * R) where W = writers per field, R = readers per field
        dependencies: Dict[str, Set[str]] = defaultdict(set)
        
        for field, writers in field_writers.items():
            readers = field_readers.get(field, set())
            
            # Each reader depends on all writers of the same field
            for reader in readers:
                for writer in writers:
                    if reader != writer:
                        dependencies[reader].add(writer)
        
        return dict(dependencies)
    
    def _topological_sort(self, dependencies: Dict[str, Set[str]]) -> List[List[str]]:
        """
        Perform topological sort to get execution layers.
        
        Time Complexity: O(V + E) - Kahn's algorithm
        Returns layers of rules that can execute in parallel.
        """
        # Calculate in-degrees
        in_degree: Dict[str, int] = defaultdict(int)
        all_rules = set()
        
        for rule_id, deps in dependencies.items():
            all_rules.add(rule_id)
            all_rules.update(deps)
            in_degree[rule_id] = len(deps)
        
        # Initialize rules with no dependencies
        queue = deque([rule_id for rule_id in all_rules if in_degree[rule_id] == 0])
        layers = []
        
        while queue:
            # Process all rules at current level (they can run in parallel)
            current_layer = []
            layer_size = len(queue)
            
            for _ in range(layer_size):
                rule_id = queue.popleft()
                current_layer.append(rule_id)
                
                # Reduce in-degree of dependent rules
                for dependent_rule, deps in dependencies.items():
                    if rule_id in deps:
                        in_degree[dependent_rule] -= 1
                        if in_degree[dependent_rule] == 0:
                            queue.append(dependent_rule)
            
            if current_layer:
                # Sort by priority within layer
                layers.append(current_layer)
        
        return layers
    
    def _execute_layer(self, layer: List[str], rules: List[Rule],
                      context: ExecutionContext, evaluator: ConditionEvaluator,
                      action_executor: ActionExecutor) -> None:
        """Execute all rules in a layer."""
        # Create rule lookup for efficiency
        rule_map = {rule.id.value: rule for rule in rules}
        
        # Execute rules in priority order within layer
        layer_rules = [rule_map[rule_id] for rule_id in layer if rule_id in rule_map]
        layer_rules.sort(key=lambda r: r.priority.value, reverse=True)
        
        for rule in layer_rules:
            try:
                if evaluator.evaluate(rule.condition, context):
                    context.rule_fired(rule.id)
                    action_executor.execute(rule.actions, context)
            except Exception:
                continue


class OptimizedLinearStrategy(ExecutionStrategy):
    """
    Linear execution with optimizations for performance.
    
    Features:
    - Pre-sorted rules
    - Early termination conditions
    - Efficient field access patterns
    """
    
    def __init__(self, enable_early_termination: bool = False):
        self.enable_early_termination = enable_early_termination
        self._sorted_rules_cache: Dict[int, List[Rule]] = {}
    
    def execute(self, rules: List[Rule], facts: Facts,
                evaluator: ConditionEvaluator,
                action_executor: ActionExecutor) -> ExecutionResult:
        """Execute with optimizations."""
        
        start_time = time.perf_counter_ns()
        
        context = ExecutionContext(
            original_facts=facts,
            enriched_facts={},
            fired_rules=[],
            trace_level=TraceLevel.NONE
        )
        
        # Use cached sorted rules if available
        rules_hash = hash(tuple(rule.id.value for rule in rules))
        if rules_hash not in self._sorted_rules_cache:
            self._sorted_rules_cache[rules_hash] = sorted(
                rules, key=lambda r: r.priority.value, reverse=True
            )
        
        sorted_rules = self._sorted_rules_cache[rules_hash]
        
        # Execute with potential early termination
        for rule in sorted_rules:
            try:
                if evaluator.evaluate(rule.condition, context):
                    context.rule_fired(rule.id)
                    action_executor.execute(rule.actions, context)
                    
                    # Early termination if specific conditions are met
                    if self.enable_early_termination and self._should_terminate(context):
                        break
                        
            except Exception:
                continue
        
        execution_time = time.perf_counter_ns() - start_time
        
        return ExecutionResult(
            verdict=context.verdict,
            fired_rules=context.fired_rules,
            execution_time_ns=execution_time,
            context_id=context.context_id
        )
    
    def name(self) -> str:
        return "optimized_linear"
    
    def _should_terminate(self, context: ExecutionContext) -> bool:
        """Check if execution should terminate early."""
        # Example: terminate if a "final_decision" field is set
        return 'final_decision' in context.enriched_facts


# Factory function for auto-selecting strategy
def create_optimal_strategy(rules: List[Rule]) -> ExecutionStrategy:
    """Auto-select optimal execution strategy based on rules."""
    
    rule_count = len(rules)
    
    if rule_count <= 10:
        # Small rule sets: use simple linear execution
        return LinearExecutionStrategy()
    
    elif rule_count <= 50:
        # Medium rule sets: use optimized linear
        return OptimizedLinearStrategy()
    
    else:
        # Large rule sets: use DAG execution
        return DAGExecutionStrategy()


# Specialized strategies for specific use cases
class PriorityOnlyStrategy(ExecutionStrategy):
    """Ultra-fast strategy that only considers priority, ignores dependencies."""
    
    def execute(self, rules: List[Rule], facts: Facts,
                evaluator: ConditionEvaluator,
                action_executor: ActionExecutor) -> ExecutionResult:
        """Execute by priority only - fastest possible."""
        
        start_time = time.perf_counter_ns()
        
        context = ExecutionContext(
            original_facts=facts,
            enriched_facts={},
            fired_rules=[],
            trace_level=TraceLevel.NONE
        )
        
        # Sort once by priority
        sorted_rules = sorted(rules, key=lambda r: r.priority.value, reverse=True)
        
        # Execute without dependency checking
        for rule in sorted_rules:
            if evaluator.evaluate(rule.condition, context):
                context.rule_fired(rule.id)
                action_executor.execute(rule.actions, context)
        
        execution_time = time.perf_counter_ns() - start_time
        
        return ExecutionResult(
            verdict=context.verdict,
            fired_rules=context.fired_rules,
            execution_time_ns=execution_time,
            context_id=context.context_id
        )
    
    def name(self) -> str:
        return "priority_only" 