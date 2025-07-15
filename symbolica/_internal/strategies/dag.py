"""
DAG-based Rule Execution Strategy
=================================

Dependency-aware rule ordering using directed acyclic graph analysis.
Optimizes rule execution order for maximum efficiency.
"""

from typing import List, Dict, Set, Optional, Tuple, TYPE_CHECKING
from collections import defaultdict, deque
import logging
from ...core.exceptions import DAGError, EvaluationError

if TYPE_CHECKING:
    from ...core.models import Rule
    from ...core.interfaces import ConditionEvaluator


class CircularDependencyInfo:
    """Information about detected circular dependencies."""
    
    def __init__(self, cycle_chain: List[str], field_dependencies: Dict[str, Set[str]]):
        self.cycle_chain = cycle_chain
        self.field_dependencies = field_dependencies
    
    def __str__(self):
        cycle_str = " -> ".join(self.cycle_chain + [self.cycle_chain[0]])
        
        details = []
        for i in range(len(self.cycle_chain)):
            current = self.cycle_chain[i]
            next_rule = self.cycle_chain[(i + 1) % len(self.cycle_chain)]
            
            # Find the fields that create this dependency
            if current in self.field_dependencies:
                shared_fields = []
                for field in self.field_dependencies[current]:
                    if field in self.field_dependencies.get(next_rule, set()):
                        shared_fields.append(field)
                
                if shared_fields:
                    details.append(f"  {current} depends on {next_rule} via fields: {', '.join(shared_fields)}")
                else:
                    details.append(f"  {current} -> {next_rule}")
        
        return f"Circular dependency detected: {cycle_str}\nDetails:\n" + "\n".join(details)


class DAGStrategy:
    """Execution strategy using dependency analysis and topological sorting."""
    
    def __init__(self, evaluator: 'ConditionEvaluator'):
        """Initialize DAG strategy with condition evaluator.
        
        Args:
            evaluator: Condition evaluator for field extraction
        """
        self.evaluator = evaluator
        self.logger = logging.getLogger('symbolica.DAGStrategy')
    
    def get_execution_order(self, rules: List['Rule']) -> List['Rule']:
        """Get optimal rule execution order using DAG analysis.
        
        Args:
            rules: Rules to order
            
        Returns:
            Rules ordered for optimal execution
            
        Raises:
            DAGError: If circular dependencies are detected
        """
        if len(rules) <= 1:
            return rules
        
        try:
            # Build dependency graph
            dependency_graph, field_dependencies = self._build_dependency_graph(rules)
            
            # Check for cycles with detailed information
            cycle_info = self._find_cycles_with_details(dependency_graph, field_dependencies)
            if cycle_info:
                detailed_error = f"Circular dependencies detected in rule set:\n\n{cycle_info}"
                self.logger.error(detailed_error)
                raise DAGError(detailed_error)
            
            # Perform topological sort with priority weighting
            ordered_rules = self._topological_sort_with_priority(rules, dependency_graph)
            
            self.logger.debug(f"DAG ordering completed: {[r.id for r in ordered_rules]}")
            return ordered_rules
            
        except Exception as e:
            if isinstance(e, DAGError):
                raise
            else:
                raise DAGError(f"Failed to compute DAG ordering: {str(e)}")
    
    def _build_dependency_graph(self, rules: List['Rule']) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
        """Build dependency graph based on field usage.
        
        Args:
            rules: Rules to analyze
            
        Returns:
            Tuple of (dependency_graph, field_dependencies)
            - dependency_graph: rule_id -> set of dependent rule_ids
            - field_dependencies: rule_id -> set of required fields
        """
        # Extract fields for each rule
        rule_inputs = {}  # rule_id -> set of input fields
        rule_outputs = {}  # rule_id -> set of output fields
        
        for rule in rules:
            try:
                # Get input fields from condition
                if hasattr(self.evaluator, 'extract_fields'):
                    input_fields = self.evaluator.extract_fields(rule.condition)
                else:
                    # Fallback to empty set if extraction not available
                    input_fields = set()
                
                # Get output fields from actions and facts
                output_fields = set(rule.actions.keys())
                if hasattr(rule, 'facts') and rule.facts:
                    output_fields.update(rule.facts.keys())
                
                rule_inputs[rule.id] = input_fields
                rule_outputs[rule.id] = output_fields
                
            except Exception as e:
                self.logger.warning(f"Failed to extract fields for rule {rule.id}: {e}")
                rule_inputs[rule.id] = set()
                rule_outputs[rule.id] = set(rule.actions.keys())
        
        # Build dependency graph
        dependencies = defaultdict(set)
        field_dependencies = {}
        
        for rule in rules:
            rule_id = rule.id
            required_fields = rule_inputs.get(rule_id, set())
            field_dependencies[rule_id] = required_fields
            
            # Find rules that produce required fields
            for other_rule in rules:
                if other_rule.id == rule_id:
                    continue
                
                other_outputs = rule_outputs.get(other_rule.id, set())
                
                # If other rule produces fields this rule needs
                if required_fields & other_outputs:
                    dependencies[rule_id].add(other_rule.id)
        
        return dict(dependencies), field_dependencies
    
    def _find_cycles_with_details(self, graph: Dict[str, Set[str]], 
                                 field_dependencies: Dict[str, Set[str]]) -> Optional[CircularDependencyInfo]:
        """Find cycles in dependency graph with detailed information.
        
        Args:
            graph: Dependency graph
            field_dependencies: Field dependencies for each rule
            
        Returns:
            CircularDependencyInfo if cycles exist, None otherwise
        """
        # Three-color DFS for cycle detection with path tracking
        WHITE, GRAY, BLACK = 0, 1, 2
        colors = {node: WHITE for node in graph}
        path = []
        
        def dfs(node: str) -> Optional[List[str]]:
            if colors[node] == GRAY:
                # Found a back edge - extract the cycle
                cycle_start = path.index(node)
                cycle_chain = path[cycle_start:]
                return cycle_chain
            
            if colors[node] == BLACK:
                return None  # Already processed
            
            colors[node] = GRAY
            path.append(node)
            
            # Visit neighbors
            for neighbor in graph.get(node, set()):
                if neighbor in colors:
                    cycle = dfs(neighbor)
                    if cycle:
                        return cycle
            
            colors[node] = BLACK
            path.pop()
            return None
        
        # Check each unvisited node
        for node in graph:
            if colors[node] == WHITE:
                cycle_chain = dfs(node)
                if cycle_chain:
                    return CircularDependencyInfo(cycle_chain, field_dependencies)
        
        return None
    
    def _has_cycles(self, graph: Dict[str, Set[str]]) -> bool:
        """Check if dependency graph has cycles using DFS.
        
        Args:
            graph: Dependency graph
            
        Returns:
            True if cycles exist, False otherwise
        """
        # Use the detailed cycle detection and just return boolean
        field_deps = {node: set() for node in graph}  # Empty field deps for compatibility
        return self._find_cycles_with_details(graph, field_deps) is not None
    
    def _topological_sort_with_priority(self, rules: List['Rule'], 
                                       dependencies: Dict[str, Set[str]]) -> List['Rule']:
        """Perform topological sort with priority consideration.
        
        Args:
            rules: Original rules list
            dependencies: Dependency graph
            
        Returns:
            Rules in topological order with priority weighting
        """
        # Create rule lookup
        rule_map = {rule.id: rule for rule in rules}
        
        # Calculate in-degrees
        in_degree = {rule.id: 0 for rule in rules}
        for rule_id, deps in dependencies.items():
            in_degree[rule_id] = len(deps)
        
        # Use priority queue for nodes with zero in-degree
        # Higher priority rules are processed first when dependencies are equal
        ready_queue = []
        
        # Initialize with rules having no dependencies
        for rule in rules:
            if in_degree[rule.id] == 0:
                # Insert in priority order (higher priority first)
                self._insert_by_priority(ready_queue, rule)
        
        result = []
        
        while ready_queue:
            # Process highest priority rule
            current_rule = ready_queue.pop(0)
            result.append(current_rule)
            
            # Update dependencies
            for other_rule_id in rule_map:
                if current_rule.id in dependencies.get(other_rule_id, set()):
                    in_degree[other_rule_id] -= 1
                    
                    # If all dependencies satisfied, add to ready queue
                    if in_degree[other_rule_id] == 0:
                        other_rule = rule_map[other_rule_id]
                        self._insert_by_priority(ready_queue, other_rule)
        
        # Verify all rules were processed
        if len(result) != len(rules):
            missing_rules = [r.id for r in rules if r not in result]
            raise DAGError(f"Topological sort failed: unprocessed rules {missing_rules}")
        
        return result
    
    def _insert_by_priority(self, queue: List['Rule'], rule: 'Rule') -> None:
        """Insert rule into queue maintaining priority order.
        
        Args:
            queue: Queue to insert into
            rule: Rule to insert
        """
        # Insert in descending priority order
        for i, existing_rule in enumerate(queue):
            if rule.priority > existing_rule.priority:
                queue.insert(i, rule)
                return
        
        # If not inserted, append to end
        queue.append(rule)
    
    def get_dependency_analysis(self, rules: List['Rule']) -> Dict[str, any]:
        """Get detailed dependency analysis for rules.
        
        Args:
            rules: Rules to analyze
            
        Returns:
            Dictionary with dependency statistics
        """
        if not rules:
            return {
                'total_rules': 0,
                'dependency_depth': 0,
                'independent_rules': 0,
                'dependent_rules': 0,
                'circular_dependencies': False
            }
        
        try:
            dependency_graph, field_dependencies = self._build_dependency_graph(rules)
            cycle_info = self._find_cycles_with_details(dependency_graph, field_dependencies)
            has_cycles = cycle_info is not None
            
            # Calculate statistics
            independent_rules = sum(1 for deps in dependency_graph.values() if not deps)
            dependent_rules = len(rules) - independent_rules
            
            # Calculate dependency depth (longest path)
            max_depth = self._calculate_dependency_depth(dependency_graph)
            
            result = {
                'total_rules': len(rules),
                'dependency_depth': max_depth,
                'independent_rules': independent_rules,
                'dependent_rules': dependent_rules,
                'circular_dependencies': has_cycles,
                'dependency_graph': {k: list(v) for k, v in dependency_graph.items()}
            }
            
            # Add detailed cycle information if present
            if cycle_info:
                result['cycle_details'] = {
                    'cycle_chain': cycle_info.cycle_chain,
                    'cycle_description': str(cycle_info)
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to analyze dependencies: {e}")
            return {
                'total_rules': len(rules),
                'dependency_depth': 0,
                'independent_rules': len(rules),
                'dependent_rules': 0,
                'circular_dependencies': False,
                'error': str(e)
            }
    
    def _calculate_dependency_depth(self, graph: Dict[str, Set[str]]) -> int:
        """Calculate maximum dependency depth (longest path) in the graph.
        
        Args:
            graph: Dependency graph
            
        Returns:
            Maximum depth
        """
        if not graph:
            return 0
        
        depths = {}
        
        def calculate_depth(node: str, visited: Set[str]) -> int:
            if node in visited:
                return 0  # Circular reference
            if node in depths:
                return depths[node]
            
            visited.add(node)
            max_dependency_depth = 0
            
            for dependency in graph.get(node, set()):
                dep_depth = calculate_depth(dependency, visited.copy())
                max_dependency_depth = max(max_dependency_depth, dep_depth)
            
            depths[node] = max_dependency_depth + 1
            return depths[node]
        
        # Calculate depth for all nodes
        for node in graph:
            if node not in depths:
                calculate_depth(node, set())
        
        return max(depths.values()) if depths else 0
    
 