"""
symbolica.runtime.evaluator
===========================

Pure rule evaluation engine with comprehensive expression support.

Supports 6 categories of expressions:
1. Boolean combinators   - all:, any:, not:
2. Comparison operators  - ==, !=, >, >=, <, <=  
3. Membership/containment - in, not in
4. String helpers        - startswith(), endswith(), contains()
5. Arithmetic           - +, -, *, /, %, parentheses
6. Null/missing checks  - field == null, field != null

Expression formats:
* String expressions     – "transaction_amount > 1000"
* Structured YAML trees  – { all: [...], any: [...], not: ... }
* Mixed expressions      – [ "amount > 1000", { any: [...] } ]

The engine is PURE:
- Evaluates conditions → Boolean (rule fired or not)
- Executes actions → Sets whatever fields rules specify
- Returns ALL fields that rules set
- Agents decide what to do with output fields
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Tuple, List

from .loader import get_pack
from .trace import TraceBuilder

# Import the unified AST system
try:
    from ..compiler.expressions import parse_expression
    from ..compiler.ast import ASTNode
except ImportError:
    # Fallback for cases where compiler module isn't available
    def parse_expression(expr: Any):
        """Basic fallback."""
        raise ImportError("Compiler module not available")


# ------------ AST-based expression evaluation
def _eval_tree(node: Any, facts: Dict[str, Any], cache: Dict[str, bool]) -> bool:
    """
    Evaluate expression tree using unified AST system.
    
    Converts expressions to AST nodes and evaluates them with caching.
    Supports all expression categories through the AST.
    """
    try:
        # If it's already an AST node, evaluate directly
        if isinstance(node, ASTNode):
            return bool(node.evaluate(facts, cache))
        
        # Otherwise, parse into AST first
        ast_node = parse_expression(node)
        result = ast_node.evaluate(facts, cache)
        return bool(result)
    
    except Exception as e:
        # Log error and default to False for safety
        print(f"Expression evaluation error: {e} for expression: {node}")
        return False


# ------------ main inference entrypoint
def infer(
    facts: Dict[str, Any],
    agent: str,
    trace_level: str = "compact",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Pure rule evaluation for *agent* against *facts*.

    Returns
    -------
    verdict : dict   (ALL fields that fired rules set - no filtering)
    trace   : dict   (per TraceBuilder level)
    """
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
