"""
Rule Optimizer
=============

Optimizes rule execution order and identifies performance improvements.

Features:
- Priority-based sorting
- Dependency analysis
- Field access optimization
- Execution path optimization
"""

from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict

from ..core import Rule, RuleSet, ConditionEvaluator
from .._internal.evaluator import create_evaluator


class RuleOptimizer:
    """
    Optimizes rule sets for better execution performance.
    
    Features:
    - Sorts rules by priority and dependencies
    - Analyzes field usage patterns
    - Identifies optimization opportunities
    - Generates execution hints
    """
    
    def __init__(self):
        self.evaluator = create_evaluator()
    
    def optimize(self, rules: List[Rule]) -> List[Rule]:
        """Optimize rule execution order."""
        if not rules:
            return []
        
        # Extract field dependencies
        field_analysis = self._analyze_field_dependencies(rules)
        
        # Sort by priority first, then by dependencies
        optimized_rules = self._sort_by_priority_and_dependencies(rules, field_analysis)
        
        return optimized_rules
    
    def analyze_performance(self, rules: List[Rule]) -> Dict[str, Any]:
        """Analyze rule set for performance characteristics."""
        if not rules:
            return {'total_rules': 0, 'analysis': {}}
        
        analysis = {
            'total_rules': len(rules),
            'priority_distribution': self._analyze_priority_distribution(rules),
            'field_usage': self._analyze_field_usage(rules),
            'complexity_analysis': self._analyze_complexity(rules),
            'dependency_analysis': self._analyze_dependencies(rules),
            'optimization_opportunities': self._identify_optimization_opportunities(rules)
        }
        
        return analysis
    
    def _analyze_field_dependencies(self, rules: List[Rule]) -> Dict[str, Any]:
        """Analyze field read/write dependencies between rules."""
        field_readers = defaultdict(list)
        field_writers = defaultdict(list)
        
        for rule in rules:
            # Extract fields this rule reads
            read_fields = self.evaluator.extract_fields(rule.condition)
            for field in read_fields:
                field_readers[field].append(rule.id.value)
            
            # Extract fields this rule writes
            write_fields = rule.written_fields
            for field in write_fields:
                field_writers[field].append(rule.id.value)
        
        # Find dependencies (readers depend on writers)
        dependencies = defaultdict(set)
        for field, writers in field_writers.items():
            readers = field_readers.get(field, [])
            for reader in readers:
                for writer in writers:
                    if reader != writer:
                        dependencies[reader].add(writer)
        
        return {
            'field_readers': dict(field_readers),
            'field_writers': dict(field_writers),
            'dependencies': {k: list(v) for k, v in dependencies.items()}
        }
    
    def _sort_by_priority_and_dependencies(self, rules: List[Rule], 
                                         field_analysis: Dict[str, Any]) -> List[Rule]:
        """Sort rules by priority, respecting dependencies."""
        # Create rule lookup
        rule_map = {rule.id.value: rule for rule in rules}
        dependencies = field_analysis['dependencies']
        
        # First, sort by priority (highest first)
        sorted_rules = sorted(rules, key=lambda r: r.priority.value, reverse=True)
        
        # Then adjust for dependencies within same priority groups
        priority_groups = defaultdict(list)
        for rule in sorted_rules:
            priority_groups[rule.priority.value].append(rule)
        
        final_rules = []
        for priority in sorted(priority_groups.keys(), reverse=True):
            group_rules = priority_groups[priority]
            # Sort within group by dependency order
            ordered_group = self._topological_sort_group(group_rules, dependencies)
            final_rules.extend(ordered_group)
        
        return final_rules
    
    def _topological_sort_group(self, rules: List[Rule], 
                               dependencies: Dict[str, List[str]]) -> List[Rule]:
        """Sort rules within a priority group by dependencies."""
        if len(rules) <= 1:
            return rules
        
        # Build dependency graph for this group
        rule_ids = {rule.id.value for rule in rules}
        group_deps = {}
        
        for rule in rules:
            rule_id = rule.id.value
            deps = [dep for dep in dependencies.get(rule_id, []) if dep in rule_ids]
            group_deps[rule_id] = deps
        
        # Simple topological sort
        visited = set()
        result = []
        
        def visit(rule_id: str):
            if rule_id in visited:
                return
            visited.add(rule_id)
            
            # Visit dependencies first
            for dep in group_deps.get(rule_id, []):
                visit(dep)
            
            # Find rule object and add to result
            for rule in rules:
                if rule.id.value == rule_id:
                    result.append(rule)
                    break
        
        for rule in rules:
            visit(rule.id.value)
        
        return result
    
    def _analyze_priority_distribution(self, rules: List[Rule]) -> Dict[str, Any]:
        """Analyze priority distribution."""
        priorities = [rule.priority.value for rule in rules]
        
        if not priorities:
            return {}
        
        priority_counts = defaultdict(int)
        for p in priorities:
            priority_counts[p] += 1
        
        return {
            'min': min(priorities),
            'max': max(priorities),
            'average': sum(priorities) / len(priorities),
            'distribution': dict(priority_counts),
            'unique_priorities': len(priority_counts)
        }
    
    def _analyze_field_usage(self, rules: List[Rule]) -> Dict[str, Any]:
        """Analyze field usage patterns."""
        all_read_fields = set()
        all_write_fields = set()
        field_read_counts = defaultdict(int)
        field_write_counts = defaultdict(int)
        
        for rule in rules:
            read_fields = self.evaluator.extract_fields(rule.condition)
            write_fields = rule.written_fields
            
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
            'most_read_fields': sorted(field_read_counts.items(), 
                                     key=lambda x: x[1], reverse=True)[:5],
            'most_written_fields': sorted(field_write_counts.items(), 
                                        key=lambda x: x[1], reverse=True)[:5]
        }
    
    def _analyze_complexity(self, rules: List[Rule]) -> Dict[str, Any]:
        """Analyze rule complexity."""
        expression_lengths = []
        action_counts = []
        tag_counts = []
        
        for rule in rules:
            expression_lengths.append(len(rule.condition.expression))
            action_counts.append(len(rule.actions))
            tag_counts.append(len(rule.tags))
        
        return {
            'expression_complexity': {
                'average_length': sum(expression_lengths) / len(expression_lengths) if expression_lengths else 0,
                'max_length': max(expression_lengths) if expression_lengths else 0,
                'min_length': min(expression_lengths) if expression_lengths else 0
            },
            'action_complexity': {
                'average_actions': sum(action_counts) / len(action_counts) if action_counts else 0,
                'max_actions': max(action_counts) if action_counts else 0
            },
            'tag_usage': {
                'average_tags': sum(tag_counts) / len(tag_counts) if tag_counts else 0,
                'max_tags': max(tag_counts) if tag_counts else 0
            }
        }
    
    def _analyze_dependencies(self, rules: List[Rule]) -> Dict[str, Any]:
        """Analyze rule dependencies."""
        field_analysis = self._analyze_field_dependencies(rules)
        dependencies = field_analysis['dependencies']
        
        # Count dependencies per rule
        dependency_counts = {rule_id: len(deps) for rule_id, deps in dependencies.items()}
        
        # Find cycles (simplified check)
        has_cycles = self._detect_cycles(dependencies)
        
        return {
            'total_dependencies': sum(len(deps) for deps in dependencies.values()),
            'rules_with_dependencies': len([r for r in dependency_counts.values() if r > 0]),
            'max_dependencies_per_rule': max(dependency_counts.values()) if dependency_counts else 0,
            'average_dependencies': (sum(dependency_counts.values()) / len(dependency_counts) 
                                   if dependency_counts else 0),
            'has_cycles': has_cycles
        }
    
    def _detect_cycles(self, dependencies: Dict[str, List[str]]) -> bool:
        """Simple cycle detection in dependency graph."""
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            if node in rec_stack:
                return True
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in dependencies.get(node, []):
                if has_cycle(neighbor):
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in dependencies:
            if has_cycle(node):
                return True
        
        return False
    
    def _identify_optimization_opportunities(self, rules: List[Rule]) -> List[str]:
        """Identify potential optimization opportunities."""
        opportunities = []
        
        # Check for many rules with same priority
        priority_counts = defaultdict(int)
        for rule in rules:
            priority_counts[rule.priority.value] += 1
        
        for priority, count in priority_counts.items():
            if count > 10:
                opportunities.append(f"Many rules ({count}) have same priority {priority} - consider using different priorities for better ordering")
        
        # Check for very long expressions
        for rule in rules:
            if len(rule.condition.expression) > 200:
                opportunities.append(f"Rule {rule.id.value} has very long expression ({len(rule.condition.expression)} chars) - consider simplifying")
        
        # Check for rules with many actions
        for rule in rules:
            if len(rule.actions) > 5:
                opportunities.append(f"Rule {rule.id.value} has many actions ({len(rule.actions)}) - consider splitting into multiple rules")
        
        # Check field usage patterns
        field_analysis = self._analyze_field_dependencies(rules)
        for field, writers in field_analysis['field_writers'].items():
            if len(writers) > 3:
                opportunities.append(f"Field '{field}' is written by many rules ({len(writers)}) - potential conflict source")
        
        return opportunities


# Convenience function
def optimize_rules(rules: List[Rule]) -> List[Rule]:
    """Optimize rule execution order."""
    optimizer = RuleOptimizer()
    return optimizer.optimize(rules) 