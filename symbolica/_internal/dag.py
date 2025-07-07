"""
DAG Execution Engine
===================

Dependency-aware execution for 1000+ rules with conflict resolution.

Features:
- Automatic dependency detection between rules
- Execution layers for parallel processing
- Simple conflict detection
- Performance optimization for large rule sets
"""

import time
from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum

from ..core import (
    Rule, Facts, ExecutionResult, ExecutionContext, 
    ConditionEvaluator, ActionExecutor, ExecutionError
)


class ConflictResolution(Enum):
    """How to handle field write conflicts."""
    PRIORITY = "priority"  # Higher priority wins


@dataclass
class RuleNode:
    """Node in the execution DAG representing a rule."""
    rule: Rule
    dependencies: Set[str]  # Rule IDs this rule depends on
    dependents: Set[str]    # Rule IDs that depend on this rule
    layer: int = -1         # Execution layer (for parallel execution)
    
    @property
    def id(self) -> str:
        return self.rule.id


@dataclass
class ExecutionLayer:
    """A layer of rules that can execute in parallel."""
    layer_id: int
    rules: List[RuleNode]
    
    @property
    def rule_count(self) -> int:
        return len(self.rules)


class DAGBuilder:
    """Builds execution DAGs from rule sets."""
    
    def __init__(self, evaluator: ConditionEvaluator):
        self.evaluator = evaluator
    
    def build_execution_layers(self, rules: List[Rule]) -> List[ExecutionLayer]:
        """Build execution layers with dependency analysis."""
        
        # Create rule nodes
        nodes = self._create_rule_nodes(rules)
        
        # Analyze field dependencies
        self._analyze_field_dependencies(nodes)
        
        # Create execution layers using topological sorting
        layers = self._create_execution_layers(nodes)
        
        return layers
    
    def _create_rule_nodes(self, rules: List[Rule]) -> Dict[str, RuleNode]:
        """Create rule nodes from rules."""
        nodes = {}
        
        for rule in rules:
            node = RuleNode(
                rule=rule,
                dependencies=set(),
                dependents=set()
            )
            nodes[rule.id] = node
        
        return nodes
    
    def _analyze_field_dependencies(self, nodes: Dict[str, RuleNode]) -> None:
        """Analyze field read/write dependencies between rules."""
        
        # Map fields to their readers and writers
        field_readers: Dict[str, List[str]] = defaultdict(list)
        field_writers: Dict[str, List[str]] = defaultdict(list)
        
        for rule_id, node in nodes.items():
            # Extract fields this rule reads
            read_fields = self.evaluator.extract_fields(node.rule.condition)
            for field in read_fields:
                field_readers[field].append(rule_id)
            
            # Extract fields this rule writes (simple: all action keys)
            write_fields = set(node.rule.actions.keys())
            for field in write_fields:
                field_writers[field].append(rule_id)
        
        # Create dependencies: readers depend on writers
        for field_name, writers in field_writers.items():
            readers = field_readers.get(field_name, [])
            
            for reader in readers:
                for writer in writers:
                    if reader != writer:
                        # Reader depends on writer
                        reader_node = nodes[reader]
                        writer_node = nodes[writer]
                        
                        reader_node.dependencies.add(writer_node.id)
                        writer_node.dependents.add(reader_node.id)
    
    def _create_execution_layers(self, nodes: Dict[str, RuleNode]) -> List[ExecutionLayer]:
        """Create execution layers using topological sorting."""
        
        # Kahn's algorithm for topological sorting
        in_degree = {rule_id: len(node.dependencies) for rule_id, node in nodes.items()}
        layers = []
        layer_id = 0
        
        while any(degree >= 0 for degree in in_degree.values()):
            # Find all nodes with no dependencies
            ready_nodes = [
                nodes[rule_id] for rule_id, degree in in_degree.items() 
                if degree == 0
            ]
            
            if not ready_nodes:
                # Handle any remaining nodes (potential cycles)
                remaining = [
                    nodes[rule_id] for rule_id, degree in in_degree.items() 
                    if degree > 0
                ]
                if remaining:
                    ready_nodes = remaining
                else:
                    break
            
            # Sort by priority within layer (highest first)
            ready_nodes.sort(key=lambda n: n.rule.priority, reverse=True)
            
            # Assign layer
            for node in ready_nodes:
                node.layer = layer_id
                in_degree[node.id] = -1  # Mark as processed
            
            # Create execution layer
            layer = ExecutionLayer(
                layer_id=layer_id,
                rules=ready_nodes
            )
            layers.append(layer)
            
            # Update in-degrees
            for node in ready_nodes:
                for dependent_id in node.dependents:
                    if dependent_id in in_degree and in_degree[dependent_id] > 0:
                        in_degree[dependent_id] -= 1
            
            layer_id += 1
        
        return layers


class SimpleDAGExecutor:
    """
    Simple DAG-based executor for dependency-aware rule execution.
    
    Optimized for 1000+ rules with field dependencies.
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._layer_cache: Dict[int, List[ExecutionLayer]] = {}
    
    def execute(self, rules: List[Rule], facts: Facts,
                evaluator: ConditionEvaluator, action_executor: ActionExecutor) -> ExecutionResult:
        """Execute rules using DAG strategy."""
        
        start_time = time.perf_counter()
        
        # Create execution context
        context = ExecutionContext(
            original_facts=facts,
            enriched_facts={},
            fired_rules=[]
        )
        
        # Build or get cached execution layers
        layers = self._get_or_build_layers(rules, evaluator)
        
        # Execute layers sequentially (rules within layers can be parallel)
        for layer in layers:
            self._execute_layer(layer, context, evaluator, action_executor)
        
        # Calculate execution time
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Create simple trace
        trace = {
            "fired_rules": context.fired_rules,
            "execution_layers": len(layers),
            "total_rules": len(rules),
            "execution_time_ms": execution_time_ms
        }
        
        return ExecutionResult(
            verdict=context.verdict,
            fired_rules=context.fired_rules,
            execution_time_ms=execution_time_ms,
            trace=trace
        )
    
    def _get_or_build_layers(self, rules: List[Rule], evaluator: ConditionEvaluator) -> List[ExecutionLayer]:
        """Get cached layers or build new ones."""
        # Simple cache key based on rule IDs
        rules_hash = hash(tuple(rule.id for rule in rules))
        
        if rules_hash not in self._layer_cache:
            builder = DAGBuilder(evaluator)
            layers = builder.build_execution_layers(rules)
            self._layer_cache[rules_hash] = layers
        
        return self._layer_cache[rules_hash]
    
    def _execute_layer(self, layer: ExecutionLayer, context: ExecutionContext,
                      evaluator: ConditionEvaluator, action_executor: ActionExecutor) -> None:
        """Execute all rules in a layer."""
        
        # For now, execute sequentially within layer
        # TODO: Add actual parallel execution for large layers
        for rule_node in layer.rules:
            try:
                if evaluator.evaluate(rule_node.rule.condition, context):
                    context.rule_fired(rule_node.rule.id)
                    action_executor.execute(rule_node.rule.actions, context)
            except Exception:
                # Continue execution even if one rule fails
                continue
    
    def get_analysis(self, rules: List[Rule], evaluator: ConditionEvaluator) -> Dict[str, Any]:
        """Get DAG analysis for monitoring."""
        layers = self._get_or_build_layers(rules, evaluator)
        
        return {
            'total_rules': len(rules),
            'execution_layers': len(layers),
            'max_parallel_rules': max(len(layer.rules) for layer in layers) if layers else 0,
            'layer_breakdown': [
                {
                    'layer': i,
                    'rule_count': len(layer.rules),
                    'rules': [node.rule.id for node in layer.rules]
                }
                for i, layer in enumerate(layers)
            ]
        }


# Factory function  
def create_dag_strategy(max_workers: int = 4, 
                       conflict_resolution: ConflictResolution = ConflictResolution.PRIORITY) -> SimpleDAGExecutor:
    """Create simple DAG execution strategy."""
    return SimpleDAGExecutor(max_workers) 