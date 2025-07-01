"""
symbolica.runtime.evaluator
===========================

Pure rule evaluation engine. Supports:

* inline infix conditions  – "x == 1 and y > 2"
* structured YAML trees   – all / any / not lists
* chaining via then.set   – merged into facts during same pass
* per-request memo cache
* trace levels: compact | verbose | debug  (via TraceBuilder)

The engine is PURE:
- Evaluates conditions → Boolean (rule fired or not)
- Executes actions → Sets whatever fields rules specify
- Returns ALL fields that rules set
- Agents decide what to do with output fields
"""
from __future__ import annotations

import ast
import operator
import uuid
from typing import Any, Dict, Tuple, List

from .loader import get_pack
from .trace import TraceBuilder

# ------------ tiny secure expression evaluator for leaf predicate strings
_BIN_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
}


def _literal(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):     # py ≥3.8
        return node.value
    if isinstance(node, ast.Num):          # py ≤3.7
        return node.n
    if isinstance(node, ast.Str):
        return node.s
    raise SyntaxError("unsupported literal")


def _eval_expr(expr: str, facts: Dict[str, Any]) -> bool:
    """
    Evaluate a restricted boolean expression safely.
    Supports literals, variable names, comparisons, boolean ops.
    """
    tree = ast.parse(expr, mode="eval").body

    def walk(n: ast.AST) -> Any:
        if isinstance(n, ast.BoolOp):
            vals = [walk(v) for v in n.values]
            return all(vals) if isinstance(n.op, ast.And) else any(vals)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            return not walk(n.operand)
        if isinstance(n, ast.Compare):
            left = walk(n.left)
            for op, right_raw in zip(n.ops, n.comparators):
                right = walk(right_raw)
                if not _BIN_OPS[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(n, ast.Name):
            return facts.get(n.id)
        return _literal(n)

    return bool(walk(tree))


# ------------ recursive evaluation for structured YAML form
def _eval_tree(node: Any, facts: Dict[str, Any], cache: Dict[str, bool]) -> bool:
    if isinstance(node, str):
        if node not in cache:
            cache[node] = _eval_expr(node, facts)
        return cache[node]
    if "all" in node:
        return all(_eval_tree(n, facts, cache) for n in node["all"])
    if "any" in node:
        return any(_eval_tree(n, facts, cache) for n in node["any"])
    if "not" in node:
        return not _eval_tree(node["not"], facts, cache)
    raise ValueError("Bad condition tree")


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
