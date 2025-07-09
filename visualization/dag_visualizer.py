"""
DAG Visualizer for Rule Dependencies
====================================

Visualizes rule dependencies and execution order as a directed acyclic graph.
"""

from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict, deque


class DAGVisualizer:
    """Visualizes rule dependencies and execution order."""
    
    def __init__(self, rules: List[Any]):
        self.rules = rules
        self.rule_map = {rule.id: rule for rule in rules}
        self.dependencies = self._build_dependencies()
        self.execution_order = self._compute_execution_order()
    
    def _build_dependencies(self) -> Dict[str, Set[str]]:
        """Build dependency graph based on rule priorities, conditions, and chaining."""
        dependencies = defaultdict(set)
        
        # Sort rules by priority (higher priority = executed first)
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)
        
        for i, rule in enumerate(sorted_rules):
            # Rules with lower priority depend on higher priority rules
            for j in range(i):
                if self._rules_conflict(rule, sorted_rules[j]):
                    dependencies[rule.id].add(sorted_rules[j].id)
            
            # Also check for field dependencies
            rule_fields = self._extract_fields_from_condition(rule.condition)
            for other_rule in sorted_rules[:i]:
                other_actions = self._extract_fields_from_actions(other_rule.actions)
                if rule_fields.intersection(other_actions):
                    dependencies[rule.id].add(other_rule.id)
        
        # Add explicit rule chaining dependencies
        rule_map = {rule.id: rule for rule in self.rules}
        for rule in self.rules:
            for triggered_rule_id in getattr(rule, 'triggers', []):
                if triggered_rule_id in rule_map:
                    # Triggered rule depends on the triggering rule
                    dependencies[triggered_rule_id].add(rule.id)
        
        return dict(dependencies)
    
    def _rules_conflict(self, rule1: Any, rule2: Any) -> bool:
        """Check if two rules potentially conflict."""
        # Simple heuristic: if they have overlapping field access
        fields1 = self._extract_fields_from_condition(rule1.condition)
        fields2 = self._extract_fields_from_condition(rule2.condition)
        
        actions1 = self._extract_fields_from_actions(rule1.actions)
        actions2 = self._extract_fields_from_actions(rule2.actions)
        
        # Check if rule1's conditions depend on rule2's actions
        return bool(fields1.intersection(actions2))
    
    def _extract_fields_from_condition(self, condition: str) -> Set[str]:
        """Extract field names from a condition string."""
        import re
        # Simple regex to find field references
        fields = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', condition)
        # Filter out common operators and keywords
        keywords = {'and', 'or', 'not', 'in', 'true', 'false', 'True', 'False'}
        return {f for f in fields if f not in keywords and not f.isdigit()}
    
    def _extract_fields_from_actions(self, actions: Dict[str, Any]) -> Set[str]:
        """Extract field names from actions dictionary."""
        return set(actions.keys())
    
    def _compute_execution_order(self) -> List[List[str]]:
        """Compute topological execution order (levels)."""
        # Compute in-degrees
        in_degree = defaultdict(int)
        all_rules = set(rule.id for rule in self.rules)
        
        for rule_id in all_rules:
            in_degree[rule_id] = 0
        
        for rule_id, deps in self.dependencies.items():
            for dep in deps:
                in_degree[rule_id] += 1
        
        # Topological sort by levels
        levels = []
        queue = deque([rule_id for rule_id in all_rules if in_degree[rule_id] == 0])
        
        while queue:
            current_level = []
            for _ in range(len(queue)):
                rule_id = queue.popleft()
                current_level.append(rule_id)
                
                # Reduce in-degree for dependent rules
                for dependent in all_rules:
                    if rule_id in self.dependencies.get(dependent, set()):
                        in_degree[dependent] -= 1
                        if in_degree[dependent] == 0:
                            queue.append(dependent)
            
            if current_level:
                # Sort by priority within level
                current_level.sort(key=lambda r: self.rule_map[r].priority, reverse=True)
                levels.append(current_level)
        
        return levels
    
    def get_dependency_graph(self) -> Dict[str, Dict[str, Any]]:
        """Get the full dependency graph with metadata."""
        graph = {}
        
        for rule in self.rules:
            graph[rule.id] = {
                'rule': rule,
                'dependencies': list(self.dependencies.get(rule.id, set())),
                'dependents': [
                    r_id for r_id, deps in self.dependencies.items() 
                    if rule.id in deps
                ],
                'level': self._get_rule_level(rule.id),
                'priority': rule.priority
            }
        
        return graph
    
    def _get_rule_level(self, rule_id: str) -> int:
        """Get the execution level for a rule."""
        for level, rules in enumerate(self.execution_order):
            if rule_id in rules:
                return level
        return -1
    
    def print_execution_order(self) -> None:
        """Print the execution order by levels."""
        print("\nRule Execution Order:")
        print("=" * 50)
        
        for level, rules in enumerate(self.execution_order):
            print(f"\nLevel {level}:")
            for rule_id in rules:
                rule = self.rule_map[rule_id]
                deps = self.dependencies.get(rule_id, set())
                deps_str = f" (depends on: {', '.join(sorted(deps))})" if deps else ""
                print(f"  - {rule_id} [priority: {rule.priority}]{deps_str}")
    
    def print_dependency_graph(self) -> None:
        """Print the full dependency graph including rule chaining."""
        print("\nRule Dependency Graph:")
        print("=" * 50)
        
        graph = self.get_dependency_graph()
        
        for rule_id in sorted(graph.keys()):
            node = graph[rule_id]
            rule = node['rule']
            
            print(f"\n{rule_id}:")
            print(f"  Priority: {node['priority']}")
            print(f"  Level: {node['level']}")
            
            # Show triggers (rules this one will trigger)
            triggers = getattr(rule, 'triggers', [])
            if triggers:
                print(f"  Triggers: {', '.join(triggers)}")
            
            if node['dependencies']:
                print(f"  Depends on: {', '.join(sorted(node['dependencies']))}")
            
            if node['dependents']:
                print(f"  Required by: {', '.join(sorted(node['dependents']))}")
            
            if not node['dependencies'] and not node['dependents'] and not triggers:
                print("  Independent rule")
    
    def to_graphviz(self) -> str:
        """Generate Graphviz DOT format for visualization including rule chaining."""
        lines = ["digraph RuleDependencies {"]
        lines.append("  rankdir=TB;")
        lines.append("  node [shape=box, style=rounded];")
        
        # Add nodes with styling based on level
        colors = ["lightblue", "lightgreen", "lightyellow", "lightcoral", "lightpink"]
        
        for level, rules in enumerate(self.execution_order):
            color = colors[level % len(colors)]
            for rule_id in rules:
                rule = self.rule_map[rule_id]
                label = f"{rule_id}\\npriority: {rule.priority}"
                # Add triggers info to label if present
                triggers = getattr(rule, 'triggers', [])
                if triggers:
                    label += f"\\ntriggers: {len(triggers)}"
                lines.append(f'  "{rule_id}" [label="{label}", fillcolor="{color}", style="filled,rounded"];')
        
        # Add dependency edges (solid lines)
        for rule_id, deps in self.dependencies.items():
            for dep in deps:
                # Check if this is a trigger relationship
                dep_rule = self.rule_map.get(dep)
                is_trigger = dep_rule and rule_id in getattr(dep_rule, 'triggers', [])
                
                if is_trigger:
                    # Trigger relationships use dashed blue arrows
                    lines.append(f'  "{dep}" -> "{rule_id}" [color=blue, style=dashed, label="triggers"];')
                else:
                    # Regular dependencies use solid black arrows
                    lines.append(f'  "{dep}" -> "{rule_id}";')
        
        # Add level grouping
        for level, rules in enumerate(self.execution_order):
            if len(rules) > 1:
                rule_list = " ".join(f'"{r}"' for r in rules)
                lines.append(f"  {{ rank=same; {rule_list} }}")
        
        lines.append("}")
        return "\n".join(lines)
    
    def save_graphviz(self, filename: str) -> None:
        """Save Graphviz DOT file."""
        with open(filename, 'w') as f:
            f.write(self.to_graphviz())
        print(f"Graphviz DOT file saved to: {filename}")
        print("To render: dot -Tpng {filename} -o output.png")
    
    def get_critical_path(self) -> List[str]:
        """Get the critical path (longest dependency chain)."""
        def dfs_longest_path(rule_id: str, visited: Set[str]) -> List[str]:
            if rule_id in visited:
                return []
            
            visited.add(rule_id)
            longest = []
            
            for dep in self.dependencies.get(rule_id, set()):
                path = dfs_longest_path(dep, visited.copy())
                if len(path) > len(longest):
                    longest = path
            
            visited.remove(rule_id)
            return longest + [rule_id]
        
        critical_path = []
        for rule_id in self.rule_map.keys():
            path = dfs_longest_path(rule_id, set())
            if len(path) > len(critical_path):
                critical_path = path
        
        return critical_path
    
    def print_critical_path(self) -> None:
        """Print the critical path analysis."""
        path = self.get_critical_path()
        
        print("\nCritical Path (Longest Dependency Chain):")
        print("=" * 50)
        
        if not path:
            print("No dependencies found - all rules are independent")
            return
        
        for i, rule_id in enumerate(path):
            rule = self.rule_map[rule_id]
            arrow = " -> " if i < len(path) - 1 else ""
            print(f"{rule_id} [priority: {rule.priority}]{arrow}", end="")
        
        print(f"\n\nTotal chain length: {len(path)} rules")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get dependency statistics."""
        graph = self.get_dependency_graph()
        
        return {
            'total_rules': len(self.rules),
            'total_dependencies': sum(len(deps) for deps in self.dependencies.values()),
            'execution_levels': len(self.execution_order),
            'independent_rules': len([r for r in graph.values() 
                                   if not r['dependencies'] and not r['dependents']]),
            'max_dependencies': max([len(deps) for deps in self.dependencies.values()] + [0]),
            'critical_path_length': len(self.get_critical_path()),
            'parallelization_potential': sum(len(level) for level in self.execution_order) / len(self.execution_order) if self.execution_order else 0
        }
    
    def print_stats(self) -> None:
        """Print dependency statistics."""
        stats = self.get_stats()
        
        print("\nDependency Analysis Statistics:")
        print("=" * 50)
        print(f"Total rules: {stats['total_rules']}")
        print(f"Total dependencies: {stats['total_dependencies']}")
        print(f"Execution levels: {stats['execution_levels']}")
        print(f"Independent rules: {stats['independent_rules']}")
        print(f"Max dependencies per rule: {stats['max_dependencies']}")
        print(f"Critical path length: {stats['critical_path_length']}")
        print(f"Average parallelization: {stats['parallelization_potential']:.1f} rules per level") 