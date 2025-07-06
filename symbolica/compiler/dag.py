"""
symbolica.compiler.dag
======================

Native AST + DAG execution system for Symbolica.

Features:
- Rule chaining based on field dependencies
- Parallel execution of independent rules  
- Priority-based conflict resolution
- AST nodes embedded in DAG for direct execution
"""

from __future__ import annotations

import re
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Import unified AST system for embedding in DAG nodes
try:
    from .ast import parse_expression, ASTNode
except ImportError:
    # Fallback for cases where AST not available
    ASTNode = Any
    def parse_expression(expr: Any) -> Any:
        return expr


class NodeType(Enum):
    """Types of DAG nodes."""
    RULE = "rule"
    FIELD = "field"


@dataclass
class DAGNode:
    """A node in the execution DAG."""
    id: str
    type: NodeType
    dependencies: Set[str]  # Node IDs this depends on
    dependents: Set[str]    # Node IDs that depend on this


@dataclass
class RuleNode(DAGNode):
    """A rule node with embedded AST."""
    priority: int
    condition_ast: ASTNode      # Parsed condition for direct execution
    actions: Dict[str, Any]     # Actions to execute when rule fires
    reads: Set[str]             # Field names this rule reads
    writes: Set[str]            # Field names this rule writes
    
    def __post_init__(self):
        self.type = NodeType.RULE


@dataclass
class FieldNode(DAGNode):
    """A field node representing data flow."""
    is_input: bool              # True if comes from facts, False if computed
    producers: Set[str]         # Rule IDs that write this field
    consumers: Set[str]         # Rule IDs that read this field
    
    def __post_init__(self):
        self.type = NodeType.FIELD


@dataclass 
class Conflict:
    """A conflict between rules."""
    field: str
    rules: List[str]
    message: str
    resolvable: bool    # True if priority can resolve it


@dataclass
class ExecutionLayer:
    """A layer of rules that can execute in parallel."""
    layer_id: int
    rules: List[str]    # Rule IDs that can execute in parallel
    description: str


@dataclass
class ExecutionDAG:
    """Complete execution DAG for runtime."""
    nodes: Dict[str, DAGNode]           # All nodes (rules + fields)
    rules: Dict[str, RuleNode]          # Just rule nodes
    fields: Dict[str, FieldNode]        # Just field nodes
    execution_layers: List[ExecutionLayer]  # Parallel execution plan
    conflicts: List[Conflict]
    input_fields: Set[str]              # Fields from facts
    output_fields: Set[str]             # Final output fields


class ExecutionDAGBuilder:
    """Builds native execution DAG with embedded ASTs."""
    
    def build(self, rules: List[Dict[str, Any]]) -> ExecutionDAG:
        """Build complete execution DAG for runtime."""
        
        # Step 1: Create rule nodes with embedded ASTs
        rule_nodes, field_usage = self._create_rule_nodes(rules)
        
        # Step 2: Create field nodes
        field_nodes = self._create_field_nodes(field_usage)
        
        # Step 3: Build dependencies between rules
        self._build_rule_dependencies(rule_nodes, field_nodes)
        
        # Step 4: Detect conflicts
        conflicts = self._detect_conflicts(rule_nodes, field_nodes)
        
        # Step 5: Build execution layers for parallel execution
        execution_layers = self._build_execution_layers(rule_nodes)
        
        # Step 6: Classify input/output fields
        input_fields, output_fields = self._classify_fields(field_nodes)
        
        # Combine all nodes
        all_nodes = {**rule_nodes, **field_nodes}
        
        return ExecutionDAG(
            nodes=all_nodes,
            rules=rule_nodes,
            fields=field_nodes,
            execution_layers=execution_layers,
            conflicts=conflicts,
            input_fields=input_fields,
            output_fields=output_fields
        )
    
    def _create_rule_nodes(self, rules: List[Dict[str, Any]]) -> Tuple[Dict[str, RuleNode], Dict[str, Dict[str, Set[str]]]]:
        """Create rule nodes with embedded ASTs and track field usage."""
        rule_nodes = {}
        field_usage = defaultdict(lambda: {"readers": set(), "writers": set()})
        
        for rule_data in rules:
            rule_id = rule_data["id"]
            
            # Parse condition into AST for direct execution
            condition_ast = parse_expression(rule_data.get("if", ""))
            
            # Extract field usage using utility functions
            reads = extract_read_fields(rule_data.get("if", ""))
            writes = extract_write_fields(rule_data.get("then", {}))
            
            # Create rule node
            rule_node = RuleNode(
                id=rule_id,
                type=NodeType.RULE,
                dependencies=set(),  # Will be filled later
                dependents=set(),
                priority=rule_data.get("priority", 50),
                condition_ast=condition_ast,
                actions=rule_data.get("then", {}),
                reads=reads,
                writes=writes
            )
            
            rule_nodes[rule_id] = rule_node
            
            # Track field usage
            for field in reads:
                field_usage[field]["readers"].add(rule_id)
            for field in writes:
                field_usage[field]["writers"].add(rule_id)
        
        return rule_nodes, field_usage
    
    def _create_field_nodes(self, field_usage: Dict[str, Dict[str, Set[str]]]) -> Dict[str, FieldNode]:
        """Create field nodes from usage information."""
        field_nodes = {}
        
        for field_name, usage in field_usage.items():
            is_input = len(usage["writers"]) == 0  # No writers = input field
            
            field_node = FieldNode(
                id=field_name,
                type=NodeType.FIELD,
                dependencies=set(usage["writers"]),  # Depends on rules that write it
                dependents=set(usage["readers"]),    # Rules that read it depend on this
                is_input=is_input,
                producers=usage["writers"],
                consumers=usage["readers"]
            )
            
            field_nodes[field_name] = field_node
        
        return field_nodes
    
    def _build_rule_dependencies(self, rule_nodes: Dict[str, RuleNode], field_nodes: Dict[str, FieldNode]) -> None:
        """Build dependencies between rules based on data flow."""
        for rule_id, rule_node in rule_nodes.items():
            # Rule depends on other rules that produce fields it reads
            for read_field in rule_node.reads:
                if read_field in field_nodes:
                    for producer_rule in field_nodes[read_field].producers:
                        if producer_rule != rule_id:
                            rule_node.dependencies.add(producer_rule)
                            rule_nodes[producer_rule].dependents.add(rule_id)
    
    def _classify_fields(self, field_nodes: Dict[str, FieldNode]) -> Tuple[Set[str], Set[str]]:
        """Classify fields as input or output."""
        input_fields = {name for name, field in field_nodes.items() if field.is_input}
        output_fields = {name for name, field in field_nodes.items() 
                        if field.producers and not field.consumers}
        return input_fields, output_fields
    
    def _detect_conflicts(self, rule_nodes: Dict[str, RuleNode], 
                         field_nodes: Dict[str, FieldNode]) -> List[Conflict]:
        """Detect conflicts with priority-based resolution."""
        conflicts = []
        
        for field_name, field_node in field_nodes.items():
            if len(field_node.producers) > 1:
                field_conflicts = self._detect_field_conflicts(field_name, field_node, rule_nodes)
                conflicts.extend(field_conflicts)
        
        return conflicts
    
    def _detect_field_conflicts(self, field_name: str, field_node: FieldNode, rule_nodes: Dict[str, RuleNode]) -> List[Conflict]:
        """Detect conflicts for a specific field."""
        conflicts = []
        producers = list(field_node.producers)
        
        # Group producers by priority
        priority_groups = self._group_by_priority(producers, rule_nodes)
        
        # Check for same-priority conflicts (unresolvable)
        conflicts.extend(self._detect_same_priority_conflicts(field_name, priority_groups))
        
        # Check for different-priority conflicts (resolvable)
        if len(priority_groups) > 1:
            conflicts.append(self._create_resolvable_conflict(field_name, priority_groups))
        
        return conflicts
    
    def _group_by_priority(self, producers: List[str], rule_nodes: Dict[str, RuleNode]) -> Dict[int, List[str]]:
        """Group rule producers by their priority."""
        priority_groups = defaultdict(list)
        for rule_id in producers:
            priority = rule_nodes[rule_id].priority
            priority_groups[priority].append(rule_id)
        return priority_groups
    
    def _detect_same_priority_conflicts(self, field_name: str, priority_groups: Dict[int, List[str]]) -> List[Conflict]:
        """Detect unresolvable conflicts where rules have the same priority."""
        conflicts = []
        for priority, rules in priority_groups.items():
            if len(rules) > 1:
                conflicts.append(Conflict(
                    field=field_name,
                    rules=rules,
                    message=f"Rules {rules} both write '{field_name}' with same priority ({priority})",
                    resolvable=False
                ))
        return conflicts
    
    def _create_resolvable_conflict(self, field_name: str, priority_groups: Dict[int, List[str]]) -> Conflict:
        """Create a resolvable conflict for different-priority rules."""
        sorted_priorities = sorted(priority_groups.keys(), reverse=True)
        all_producers = []
        for p in sorted_priorities:
            all_producers.extend(priority_groups[p])
        
        return Conflict(
            field=field_name,
            rules=all_producers,
            message=f"Rules {all_producers} write '{field_name}' with priorities {sorted_priorities} (resolvable by priority)",
            resolvable=True
        )
    
    def _build_execution_layers(self, rule_nodes: Dict[str, RuleNode]) -> List[ExecutionLayer]:
        """Build execution layers for parallel execution."""
        layers = []
        remaining_rules = set(rule_nodes.keys())
        layer_id = 0
        
        while remaining_rules:
            # Find rules with no unresolved dependencies
            ready_rules = []
            for rule_id in remaining_rules:
                rule = rule_nodes[rule_id]
                unresolved_deps = rule.dependencies & remaining_rules
                if not unresolved_deps:
                    ready_rules.append(rule_id)
            
            if not ready_rules:
                # Circular dependency - break it by priority
                highest_priority_rule = max(remaining_rules, 
                                          key=lambda r: rule_nodes[r].priority)
                ready_rules = [highest_priority_rule]
            
            # Sort by priority within layer (highest first)
            ready_rules.sort(key=lambda r: -rule_nodes[r].priority)
            
            layers.append(ExecutionLayer(
                layer_id=layer_id,
                rules=ready_rules,
                description=f"Layer {layer_id}: {len(ready_rules)} parallel rules"
            ))
            
            # Remove processed rules
            for rule_id in ready_rules:
                remaining_rules.remove(rule_id)
            
            layer_id += 1
        
        return layers


def build_execution_dag(rules: List[Dict[str, Any]]) -> ExecutionDAG:
    """Build execution DAG for runtime - main entry point."""
    builder = ExecutionDAGBuilder()
    return builder.build(rules)


def visualize_execution_dag(dag: ExecutionDAG, format: str = "layers") -> str:
    """Visualize execution DAG with focus on parallel execution."""
    if format == "layers":
        return _visualize_layers(dag)
    elif format == "summary":
        return _visualize_summary(dag)
    else:
        raise ValueError(f"Unknown format: {format}")


def _visualize_layers(dag: ExecutionDAG) -> str:
    """Show parallel execution layers."""
    lines = []
    
    lines.append("🚀 Parallel Execution Plan")
    lines.append("=" * 40)
    
    for layer in dag.execution_layers:
        lines.append(f"\n📋 {layer.description}")
        for rule_id in layer.rules:
            rule = dag.rules[rule_id]
            deps = f" (deps: {', '.join(sorted(rule.dependencies))})" if rule.dependencies else ""
            lines.append(f"├── {rule_id} [pri:{rule.priority}]{deps}")
            lines.append(f"│   reads: {', '.join(sorted(rule.reads))}")
            lines.append(f"│   writes: {', '.join(sorted(rule.writes))}")
    
    # Show conflicts
    if dag.conflicts:
        lines.append(f"\n⚠️  Conflicts ({len(dag.conflicts)}):")
        for conflict in dag.conflicts:
            icon = "✅" if conflict.resolvable else "❌"
            lines.append(f"├── {icon} {conflict.message}")
    
    return "\n".join(lines)


def _visualize_summary(dag: ExecutionDAG) -> str:
    """Summary of execution capabilities."""
    lines = []
    lines.append("📊 Execution DAG Summary")
    lines.append("=" * 25)
    lines.append(f"Rules: {len(dag.rules)}")
    lines.append(f"Execution Layers: {len(dag.execution_layers)}")
    lines.append(f"Parallel Opportunities: {sum(len(layer.rules) for layer in dag.execution_layers if len(layer.rules) > 1)}")
    lines.append(f"Input Fields: {len(dag.input_fields)}")
    lines.append(f"Output Fields: {len(dag.output_fields)}")
    lines.append(f"Conflicts: {len(dag.conflicts)}")
    
    resolvable = sum(1 for c in dag.conflicts if c.resolvable)
    unresolvable = len(dag.conflicts) - resolvable
    
    if dag.conflicts:
        lines.append(f"├── Resolvable: {resolvable}")
        lines.append(f"├── Unresolvable: {unresolvable}")
    
    return "\n".join(lines)


# Legacy compatibility
def build_rule_dag(rules: List[Dict[str, Any]]) -> ExecutionDAG:
    """Legacy function - now builds execution DAG."""
    return build_execution_dag(rules)


def visualize_dag(dag: ExecutionDAG, format: str = "layers") -> str:
    """Legacy function - now visualizes execution DAG."""
    return visualize_execution_dag(dag, format)


# ============================================================================
# FIELD EXTRACTION UTILITIES
# ============================================================================

def extract_read_fields(condition: Any) -> Set[str]:
    """Extract field names from rule conditions."""
    fields = set()
    field_re = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_\.]*)\b")
    
    if isinstance(condition, str):
        _extract_from_string(condition, fields, field_re)
    elif isinstance(condition, dict):
        _extract_from_dict(condition, fields)
    elif isinstance(condition, list):
        _extract_from_list(condition, fields)
    
    return fields


def extract_write_fields(actions: Any) -> Set[str]:
    """Extract field names that actions write to."""
    fields = set()
    
    if isinstance(actions, dict):
        _extract_writes_from_dict(actions, fields)
    elif isinstance(actions, list):
        for action in actions:
            fields.update(extract_write_fields(action))
    
    return fields


def _extract_from_string(condition: str, fields: Set[str], field_re: re.Pattern[str]) -> None:
    """Extract fields from string conditions."""
    for match in field_re.findall(condition):
        if match not in {"and", "or", "not", "in", "true", "false", "null", "none"}:
            fields.add(match)


def _extract_from_dict(condition: Dict[str, Any], fields: Set[str]) -> None:
    """Extract fields from dictionary conditions."""
    for key, value in condition.items():
        if key in ["all", "any"]:
            for sub in value:
                fields.update(extract_read_fields(sub))
        elif key == "not":
            fields.update(extract_read_fields(value))


def _extract_from_list(condition: List[Any], fields: Set[str]) -> None:
    """Extract fields from list conditions."""
    for sub in condition:
        fields.update(extract_read_fields(sub))


def _extract_writes_from_dict(actions: Dict[str, Any], fields: Set[str]) -> None:
    """Extract write fields from action dictionary."""
    if "set" in actions:
        fields.update(actions["set"].keys())
    else:
        for key in actions.keys():
            if not key.startswith("_"):
                fields.add(key) 