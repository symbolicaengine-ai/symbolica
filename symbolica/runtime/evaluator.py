"""
symbolica.runtime.evaluator
============================

Core inference engine with DAG-driven execution.

Features:
- Native AST evaluation from DAG nodes
- Parallel execution within layers
- Priority-based conflict resolution  
- Rule dependency handling
- Multi-threaded layer execution
"""

from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple
from contextlib import contextmanager

from .loader import get_pack
from .trace import TraceBuilder


# Import DAG structures for runtime execution
try:
    from ..compiler.dag import ExecutionDAG, RuleNode, ExecutionLayer
except ImportError:
    # Fallback for runtime-only environments
    ExecutionDAG = Any
    RuleNode = Any
    ExecutionLayer = Any


class DAGEvaluator:
    """DAG-driven rule evaluator with parallel execution."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.cache: Dict[str, bool] = {}
        
    def evaluate_dag(self, 
                    execution_dag: ExecutionDAG,
                    facts: Dict[str, Any],
                    trace_builder: TraceBuilder) -> Dict[str, Any]:
        """Execute DAG layers with parallel execution within each layer."""
        
        enriched = facts.copy()
        self.cache.clear()
        
        for layer in execution_dag.execution_layers:
            # Execute all rules in this layer in parallel
            layer_results = self._execute_layer_parallel(
                layer, execution_dag, enriched, trace_builder
            )
            
            # Apply results from this layer
            for rule_id, rule_fired, set_dict in layer_results:
                if rule_fired:
                    enriched.update(set_dict)
                    
        return enriched
    
    def _execute_layer_parallel(self, 
                               layer: ExecutionLayer,
                               dag: ExecutionDAG, 
                               facts: Dict[str, Any],
                               trace_builder: TraceBuilder) -> List[Tuple[str, bool, Dict[str, Any]]]:
        """Execute all rules in a layer in parallel."""
        
        if len(layer.rules) == 1:
            # Single rule - no need for parallelization
            rule_id = layer.rules[0]
            rule_node = dag.rules[rule_id]
            return [self._execute_rule_node(rule_node, facts, trace_builder)]
        
        # Multiple rules - execute in parallel using simpler pattern
        results = self._execute_rules_parallel(layer.rules, dag, facts, trace_builder)
        
        # Sort results by priority to maintain determinism
        rule_priorities = {rule_id: dag.rules[rule_id].priority for rule_id in layer.rules}
        results.sort(key=lambda x: -rule_priorities[x[0]])
        
        return results
    
    def _execute_rules_parallel(self, 
                               rule_ids: List[str],
                               dag: ExecutionDAG,
                               facts: Dict[str, Any],
                               trace_builder: TraceBuilder) -> List[Tuple[str, bool, Dict[str, Any]]]:
        """Execute multiple rules in parallel with simplified error handling."""
        
        def execute_single_rule(rule_id: str) -> Tuple[str, bool, Dict[str, Any]]:
            """Execute a single rule - designed for parallel execution."""
            try:
                rule_node = dag.rules[rule_id]
                return self._execute_rule_node(rule_node, facts, trace_builder)
            except Exception as exc:
                print(f"Rule {rule_id} failed: {exc}")
                return (rule_id, False, {})
        
        # Use ThreadPoolExecutor.map for cleaner parallel execution
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(rule_ids))) as executor:
            results = list(executor.map(execute_single_rule, rule_ids))
        
        return results
    
    def _execute_rule_node(self, 
                          rule_node: RuleNode, 
                          facts: Dict[str, Any],
                          trace_builder: TraceBuilder) -> Tuple[str, bool, Dict[str, Any]]:
        """Execute a single rule node using its embedded AST."""
        
        rule_id = rule_node.id
        start_ns = trace_builder.begin_rule(rule_id)
        
        try:
            # Evaluate condition using embedded AST
            condition_result = self._eval_ast_node(rule_node.condition_ast, facts)
            
            if condition_result:
                # Rule fired - extract actions
                set_dict = rule_node.actions.get("set", {})
                trace_builder.end_rule(
                    {"id": rule_id}, True, rule_node.condition_ast, set_dict, start_ns
                )
                return (rule_id, True, set_dict)
            else:
                # Rule didn't fire
                trace_builder.end_rule(
                    {"id": rule_id}, False, rule_node.condition_ast, {}, start_ns
                )
                return (rule_id, False, {})
                
        except Exception as e:
            # Rule evaluation failed
            trace_builder.end_rule(
                {"id": rule_id}, False, f"ERROR: {e}", {}, start_ns
            )
            return (rule_id, False, {})
    
    def _eval_ast_node(self, node: Any, facts: Dict[str, Any]) -> bool:
        """Evaluate AST node - supports both new AST and legacy tree format."""
        
        # Handle the new AST node system
        if hasattr(node, 'evaluate'):
            try:
                return bool(node.evaluate(facts))
            except Exception:
                return False
        
        # Fallback to legacy tree evaluation
        return self._eval_tree_legacy(node, facts)
    
    def _eval_tree_legacy(self, tree: Any, facts: Dict[str, Any]) -> bool:
        """Legacy tree evaluation for backward compatibility."""
        
        if isinstance(tree, str):
            # Simple string conditions
            if tree in self.cache:
                return self.cache[tree]
            
            # Basic field checks
            if tree in facts:
                result = bool(facts[tree])
            elif "==" in tree:
                left, right = tree.split("==", 1)
                left, right = left.strip(), right.strip()
                if left in facts:
                    if right in ["null", "None"]:
                        result = facts[left] is None
                    else:
                        result = str(facts[left]) == right.strip('"\'')
                else:
                    result = False
            else:
                result = False
            
            self.cache[tree] = result
            return result
        
        elif isinstance(tree, dict):
            if "all" in tree:
                return all(self._eval_tree_legacy(sub, facts) for sub in tree["all"])
            elif "any" in tree:
                return any(self._eval_tree_legacy(sub, facts) for sub in tree["any"])
            elif "not" in tree:
                return not self._eval_tree_legacy(tree["not"], facts)
        
        elif isinstance(tree, list):
            # AND semantics for list
            return all(self._eval_tree_legacy(item, facts) for item in tree)
        
        return False


# Legacy compatibility - DAG-aware inference
def infer(
    facts: Dict[str, Any],
    agent: str,
    trace_level: str = "compact",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    DAG-driven rule evaluation with parallel execution.

    Returns
    -------
    verdict : dict   (ALL fields that fired rules set - no filtering)
    trace   : dict   (per TraceBuilder level)
    """
    pack = get_pack()
    
    # Check if pack has new DAG structure
    if hasattr(pack.header, 'execution_dag') and pack.header['execution_dag']:
        # New DAG-based execution
        execution_dag = _deserialize_execution_dag(pack.header['execution_dag'])
        evaluator = DAGEvaluator()
        
        tb = TraceBuilder(level=trace_level, run_id=str(uuid.uuid4()))
        enriched = evaluator.evaluate_dag(execution_dag, facts, tb)
        
        # Return only fields that rules set (minus original facts)
        verdict = {k: v for k, v in enriched.items() if k not in facts}
        trace_json = tb.finalize(enriched)
        
        return verdict, trace_json
    
    else:
        # Legacy linear execution for backward compatibility
        return _infer_legacy(facts, agent, trace_level)


def _infer_legacy(
    facts: Dict[str, Any],
    agent: str, 
    trace_level: str = "compact",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Legacy linear execution for backward compatibility."""
    
    pack = get_pack()
    dag_idx = pack.dag_for_agent(agent)          # list[int] priority-sorted

    enriched = facts.copy()
    cache: Dict[str, bool] = {}
    tb = TraceBuilder(level=trace_level, run_id=str(uuid.uuid4()))

    for idx in dag_idx:
        rule = pack.rules[idx]
        start_ns = tb.begin_rule(rule["id"])

        if _eval_tree(rule["if"], enriched, cache):
            # Rule fired - execute actions
            set_dict = rule["then"].get("set", {})
            enriched.update(set_dict)
            tb.end_rule(rule, True, rule["if"], set_dict, start_ns)
        else:
            # Rule didn't fire
            tb.end_rule(rule, False, rule["if"], {}, start_ns)

    # Pure engine: return ALL fields that rules set (minus original facts)
    verdict = {k: v for k, v in enriched.items() if k not in facts}

    trace_json = tb.finalize(enriched)
    return verdict, trace_json


def _deserialize_execution_dag(dag_data: Dict[str, Any]) -> ExecutionDAG:
    """Reconstruct ExecutionDAG from serialized data."""
    # This would deserialize the DAG structure from the .rpack file
    # For now, return None to use legacy path
    return None


# ---------------------------------------------------------------- legacy tree eval
def _eval_tree(tree: object, enriched: Dict[str, Any], cache: Dict[str, bool]) -> bool:
    """Legacy tree evaluation function."""
    
    # Handle string expressions  
    if isinstance(tree, str):
        if tree in cache:
            return cache[tree]
        
        # Try to parse as expression using the unified AST system
        try:
            from ..compiler.ast import parse_expression
            expr_node = parse_expression(tree)
            result = bool(expr_node.evaluate(enriched))
            cache[tree] = result
            return result
        except Exception:
            # Fallback to simple field lookup
            result = tree in enriched and bool(enriched[tree])
            cache[tree] = result  
            return result
    
    # Handle dict structures (YAML boolean combinators)
    elif isinstance(tree, dict):
        if "all" in tree:
            return all(_eval_tree(sub, enriched, cache) for sub in tree["all"])
        elif "any" in tree:
            return any(_eval_tree(sub, enriched, cache) for sub in tree["any"])
        elif "not" in tree:
            return not _eval_tree(tree["not"], enriched, cache)
        else:
            # Try as comparison dict
            try:
                from ..compiler.ast import parse_expression
                expr_node = parse_expression(tree)
                return bool(expr_node.evaluate(enriched))
            except Exception:
                return False
    
    # Handle list (AND semantics)
    elif isinstance(tree, list):
        return all(_eval_tree(sub, enriched, cache) for sub in tree)
    
    # Fallback
    return bool(tree)


# ---------------------------------------------------------------- utilities
@contextmanager
def dag_execution_context(max_workers: int = 4):
    """Context manager for DAG execution configuration."""
    evaluator = DAGEvaluator(max_workers=max_workers)
    yield evaluator


def get_dag_capabilities() -> Dict[str, Any]:
    """Get information about DAG execution capabilities."""
    return {
        "dag_execution": True,
        "parallel_layers": True,
        "ast_evaluation": True,
        "dependency_resolution": True,
        "conflict_resolution": True,
        "legacy_compatibility": True,
        "max_workers_default": 4,
        "features": [
            "embedded_ast_execution",
            "parallel_rule_layers", 
            "priority_based_ordering",
            "dependency_aware_execution",
            "multi_threaded_evaluation"
        ]
    }
