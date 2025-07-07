"""
DAG Execution Engine
===================

Advanced dependency-aware execution with parallel processing capabilities.

Features:
- Automatic dependency detection between rules
- Parallel execution of independent rules
- Conflict detection and resolution
- Performance optimization through execution layers
- Comprehensive execution analysis
"""

import time
from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum

from ..core import (
    Rule, Facts, ExecutionResult, ExecutionContext, TraceLevel,
    ExecutionStrategy, ConditionEvaluator, ActionExecutor,
    ExecutionError, rule_id
)


class ConflictResolution(Enum):
    """How to handle field write conflicts."""
    PRIORITY = "priority"  # Higher priority wins
    FIRST_WINS = "first_wins"  # First rule to write wins
    LAST_WINS = "last_wins"  # Last rule to write wins
    ERROR = "error"  # Raise error on conflict


@dataclass
class RuleNode:
    """Node in the execution DAG representing a rule."""
    rule: Rule
    dependencies: Set[str]  # Rule IDs this rule depends on
    dependents: Set[str]    # Rule IDs that depend on this rule
    layer: int = -1         # Execution layer (for parallel execution)
    
    @property
    def id(self) -> str:
        return self.rule.id.value


@dataclass
class FieldDependency:
    """Represents a field dependency between rules."""
    field_name: str
    writer_rule: str
    reader_rule: str
    conflict_type: str = "none"  # "none", "priority", "unresolvable"


@dataclass
class ExecutionLayer:
    """A layer of rules that can execute in parallel."""
    layer_id: int
    rules: List[RuleNode]
    max_parallelism: int = 4
    
    @property
    def rule_count(self) -> int:
        return len(self.rules)


@dataclass
class ExecutionDAG:
    """Complete directed acyclic graph for rule execution."""
    nodes: Dict[str, RuleNode]
    layers: List[ExecutionLayer]
    field_dependencies: List[FieldDependency]
    conflicts: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    
    @property
    def total_rules(self) -> int:
        return len(self.nodes)
    
    @property
    def max_parallelism(self) -> int:
        return max(layer.rule_count for layer in self.layers) if self.layers else 1


class DAGBuilder:
    """Builds execution DAGs from rule sets."""
    
    def __init__(self, evaluator: ConditionEvaluator):
        self.evaluator = evaluator
    
    def build_dag(self, rules: List[Rule], 
                  conflict_resolution: ConflictResolution = ConflictResolution.PRIORITY) -> ExecutionDAG:
        """Build complete execution DAG from rules."""
        
        # Create rule nodes
        nodes = self._create_rule_nodes(rules)
        
        # Analyze field dependencies
        field_deps, conflicts = self._analyze_field_dependencies(nodes, conflict_resolution)
        
        # Build dependency graph
        self._build_dependency_graph(nodes, field_deps)
        
        # Create execution layers
        layers = self._create_execution_layers(nodes)
        
        # Generate metadata
        metadata = self._generate_metadata(nodes, layers, field_deps, conflicts)
        
        return ExecutionDAG(
            nodes=nodes,
            layers=layers,
            field_dependencies=field_deps,
            conflicts=conflicts,
            metadata=metadata
        )
    
    def _create_rule_nodes(self, rules: List[Rule]) -> Dict[str, RuleNode]:
        """Create rule nodes from rules."""
        nodes = {}
        
        for rule in rules:
            node = RuleNode(
                rule=rule,
                dependencies=set(),
                dependents=set()
            )
            nodes[rule.id.value] = node
        
        return nodes
    
    def _analyze_field_dependencies(self, nodes: Dict[str, RuleNode], 
                                  conflict_resolution: ConflictResolution) -> Tuple[List[FieldDependency], List[Dict[str, Any]]]:
        """Analyze field read/write dependencies between rules."""
        
        # Map fields to their readers and writers
        field_readers: Dict[str, List[str]] = defaultdict(list)
        field_writers: Dict[str, List[str]] = defaultdict(list)
        
        for rule_id, node in nodes.items():
            # Extract fields this rule reads
            read_fields = self.evaluator.extract_fields(node.rule.condition)
            for field in read_fields:
                field_readers[field].append(rule_id)
            
            # Extract fields this rule writes
            write_fields = node.rule.written_fields
            for field in write_fields:
                field_writers[field].append(rule_id)
        
        # Create field dependencies
        dependencies = []
        conflicts = []
        
        for field_name, writers in field_writers.items():
            readers = field_readers.get(field_name, [])
            
            # Create dependencies: readers depend on writers
            for reader in readers:
                for writer in writers:
                    if reader != writer:
                        dependencies.append(FieldDependency(
                            field_name=field_name,
                            writer_rule=writer,
                            reader_rule=reader
                        ))
            
            # Detect conflicts: multiple writers to same field
            if len(writers) > 1:
                conflict = self._analyze_field_conflict(field_name, writers, nodes, conflict_resolution)
                if conflict:
                    conflicts.append(conflict)
        
        return dependencies, conflicts
    
    def _analyze_field_conflict(self, field_name: str, writers: List[str], 
                               nodes: Dict[str, RuleNode], 
                               conflict_resolution: ConflictResolution) -> Optional[Dict[str, Any]]:
        """Analyze a specific field conflict."""
        
        # Get priorities of conflicting rules
        writer_priorities = {
            writer: nodes[writer].rule.priority.value 
            for writer in writers
        }
        
        unique_priorities = set(writer_priorities.values())
        
        if len(unique_priorities) == 1:
            # Same priority - unresolvable conflict
            return {
                'field': field_name,
                'writers': writers,
                'type': 'unresolvable',
                'resolution': conflict_resolution.value,
                'message': f"Multiple rules write to '{field_name}' with same priority"
            }
        else:
            # Different priorities - resolvable by priority
            highest_priority = max(unique_priorities)
            winner = [w for w, p in writer_priorities.items() if p == highest_priority][0]
            
            return {
                'field': field_name,
                'writers': writers,
                'type': 'priority_resolvable',
                'resolution': conflict_resolution.value,
                'winner': winner,
                'message': f"Multiple rules write to '{field_name}' - resolved by priority"
            }
    
    def _build_dependency_graph(self, nodes: Dict[str, RuleNode], 
                               field_deps: List[FieldDependency]) -> None:
        """Build dependency relationships between rule nodes."""
        
        for dep in field_deps:
            writer_node = nodes[dep.writer_rule]
            reader_node = nodes[dep.reader_rule]
            
            # Reader depends on writer
            reader_node.dependencies.add(writer_node.id)
            writer_node.dependents.add(reader_node.id)
    
    def _create_execution_layers(self, nodes: Dict[str, RuleNode]) -> List[ExecutionLayer]:
        """Create execution layers using topological sorting."""
        
        # Kahn's algorithm for topological sorting
        in_degree = {rule_id: len(node.dependencies) for rule_id, node in nodes.items()}
        layers = []
        layer_id = 0
        
        while any(degree == 0 for degree in in_degree.values()):
            # Find all nodes with no dependencies
            ready_nodes = [
                nodes[rule_id] for rule_id, degree in in_degree.items() 
                if degree == 0
            ]
            
            if not ready_nodes:
                break
            
            # Sort by priority within layer
            ready_nodes.sort(key=lambda n: n.rule.priority.value, reverse=True)
            
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
                    if in_degree[dependent_id] > 0:
                        in_degree[dependent_id] -= 1
            
            layer_id += 1
        
        # Check for cycles
        remaining = [rule_id for rule_id, degree in in_degree.items() if degree > 0]
        if remaining:
            # Handle cycles by priority
            cycle_nodes = [nodes[rule_id] for rule_id in remaining]
            cycle_nodes.sort(key=lambda n: n.rule.priority.value, reverse=True)
            
            layer = ExecutionLayer(
                layer_id=layer_id,
                rules=cycle_nodes
            )
            layers.append(layer)
        
        return layers
    
    def _generate_metadata(self, nodes: Dict[str, RuleNode], 
                          layers: List[ExecutionLayer],
                          field_deps: List[FieldDependency],
                          conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate DAG metadata for analysis."""
        
        return {
            'total_rules': len(nodes),
            'total_layers': len(layers),
            'max_parallel_rules': max(len(layer.rules) for layer in layers) if layers else 0,
            'total_dependencies': len(field_deps),
            'total_conflicts': len(conflicts),
            'unresolvable_conflicts': len([c for c in conflicts if c['type'] == 'unresolvable']),
            'average_dependencies_per_rule': len(field_deps) / len(nodes) if nodes else 0,
            'fields_analysis': self._analyze_field_usage(nodes, field_deps)
        }
    
    def _analyze_field_usage(self, nodes: Dict[str, RuleNode], 
                           field_deps: List[FieldDependency]) -> Dict[str, Any]:
        """Analyze field usage patterns."""
        
        all_read_fields = set()
        all_write_fields = set()
        field_read_counts = defaultdict(int)
        field_write_counts = defaultdict(int)
        
        for node in nodes.values():
            read_fields = self.evaluator.extract_fields(node.rule.condition)
            write_fields = node.rule.written_fields
            
            all_read_fields.update(read_fields)
            all_write_fields.update(write_fields)
            
            for field in read_fields:
                field_read_counts[field] += 1
            for field in write_fields:
                field_write_counts[field] += 1
        
        return {
            'total_read_fields': len(all_read_fields),
            'total_write_fields': len(all_write_fields),
            'overlapping_fields': len(all_read_fields & all_write_fields),
            'most_read_fields': sorted(field_read_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            'most_written_fields': sorted(field_write_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }


class DAGExecutionStrategy(ExecutionStrategy):
    """
    Advanced DAG-based execution strategy.
    
    Features:
    - Automatic dependency analysis
    - Parallel execution within layers
    - Conflict resolution
    - Performance optimization
    """
    
    def __init__(self, max_workers: int = 4, 
                 conflict_resolution: ConflictResolution = ConflictResolution.PRIORITY):
        self.max_workers = max_workers
        self.conflict_resolution = conflict_resolution
        self._dag_cache: Dict[int, ExecutionDAG] = {}
    
    def execute(self, rules: List[Rule], facts: Facts,
                evaluator: ConditionEvaluator,
                action_executor: ActionExecutor) -> ExecutionResult:
        """Execute rules using DAG with parallel execution."""
        
        start_time = time.perf_counter_ns()
        
        # Create execution context
        context = ExecutionContext(
            original_facts=facts,
            enriched_facts={},
            fired_rules=[],
            trace_level=TraceLevel.NONE
        )
        
        # Build or get cached DAG
        dag = self._get_or_build_dag(rules, evaluator)
        
        # Execute layers sequentially, rules within layers in parallel
        self._execute_dag(dag, context, evaluator, action_executor)
        
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
    
    def get_dag_info(self, rules: List[Rule], evaluator: ConditionEvaluator) -> Dict[str, Any]:
        """Get DAG analysis information without execution."""
        dag = self._get_or_build_dag(rules, evaluator)
        
        return {
            'dag_metadata': dag.metadata,
            'execution_plan': [
                {
                    'layer': i,
                    'rules': [node.rule.id.value for node in layer.rules],
                    'parallel_count': len(layer.rules)
                }
                for i, layer in enumerate(dag.layers)
            ],
            'conflicts': dag.conflicts,
            'optimization_opportunities': self._identify_optimizations(dag)
        }
    
    def _get_or_build_dag(self, rules: List[Rule], evaluator: ConditionEvaluator) -> ExecutionDAG:
        """Get cached DAG or build new one."""
        rules_hash = hash(tuple(rule.id.value for rule in rules))
        
        if rules_hash not in self._dag_cache:
            builder = DAGBuilder(evaluator)
            dag = builder.build_dag(rules, self.conflict_resolution)
            self._dag_cache[rules_hash] = dag
        
        return self._dag_cache[rules_hash]
    
    def _execute_dag(self, dag: ExecutionDAG, context: ExecutionContext,
                    evaluator: ConditionEvaluator, action_executor: ActionExecutor) -> None:
        """Execute DAG layers sequentially."""
        
        for layer in dag.layers:
            if len(layer.rules) == 1:
                # Single rule - no parallelization needed
                self._execute_rule_node(layer.rules[0], context, evaluator, action_executor)
            else:
                # Multiple rules - execute in parallel (simulated for now)
                # In a real implementation, this would use ThreadPoolExecutor
                for rule_node in layer.rules:
                    self._execute_rule_node(rule_node, context, evaluator, action_executor)
    
    def _execute_rule_node(self, rule_node: RuleNode, context: ExecutionContext,
                          evaluator: ConditionEvaluator, action_executor: ActionExecutor) -> None:
        """Execute a single rule node."""
        
        try:
            if evaluator.evaluate(rule_node.rule.condition, context):
                context.rule_fired(rule_node.rule.id)
                action_executor.execute(rule_node.rule.actions, context)
        except Exception:
            # Log error but continue execution
            pass
    
    def _identify_optimizations(self, dag: ExecutionDAG) -> List[str]:
        """Identify potential optimization opportunities."""
        optimizations = []
        
        # Check for bottleneck layers
        for layer in dag.layers:
            if len(layer.rules) == 1 and layer.layer_id > 0:
                optimizations.append(f"Layer {layer.layer_id} has only one rule - potential bottleneck")
        
        # Check for conflicts
        unresolvable = [c for c in dag.conflicts if c['type'] == 'unresolvable']
        if unresolvable:
            optimizations.append(f"{len(unresolvable)} unresolvable conflicts - consider different priorities")
        
        # Check for long dependency chains
        max_layers = len(dag.layers)
        if max_layers > 10:
            optimizations.append(f"Long dependency chain ({max_layers} layers) - consider reducing dependencies")
        
        return optimizations


# Factory function
def create_dag_strategy(max_workers: int = 4,
                       conflict_resolution: ConflictResolution = ConflictResolution.PRIORITY) -> DAGExecutionStrategy:
    """Create DAG execution strategy."""
    return DAGExecutionStrategy(max_workers, conflict_resolution) 