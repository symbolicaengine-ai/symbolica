"""
symbolica.runtime.evaluator
===========================

Forward-chaining evaluator using a priority-sorted DAG supplied
by the runtime loader.  Supports:

* inline infix conditions  – "x == 1 and y > 2"
* structured YAML trees   – all / any / not lists
* chaining via then.set   – merged into facts during same pass
* per-request memo cache
* decision-severity ordering from rule-pack header
* trace levels: compact | verbose | debug  (via TraceBuilder)
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
    Evaluate rules for *agent* against *facts*.

    Returns
    -------
    verdict : dict   (whatever facts rules set, e.g., decision_status)
    trace   : dict   (per TraceBuilder level)
    """
    pack = get_pack()
    dag_idx = pack.dag_for_agent(agent)          # list[int] priority-sorted
    status_rank = {
        s: i
        for i, s in enumerate(
            pack.header.get(
                "status_precedence",
                ["REJECTED", "ESCALATE", "PARTIAL", "APPROVED"],
            ),
            start=1,
        )
    }

    enriched = facts.copy()
    cache: Dict[str, bool] = {}
    tb = TraceBuilder(level=trace_level, run_id=str(uuid.uuid4()))
    top_status: str | None = None
    top_reason: str | None = None
    top_priority = -1

    for idx in dag_idx:
        rule = pack.rules[idx]
        start_ns = tb.begin_rule(rule["id"])

        if _eval_tree(rule["if"], enriched, cache):
            set_dict = rule["then"].get("set", {})
            enriched.update(set_dict)
            tb.end_rule(rule, True, rule["if"], set_dict, start_ns)

            # update final decision heuristics (if project uses decision_status)
            status = set_dict.get("decision_status")
            reason = set_dict.get("reason")
            prio = rule.get("priority", 50)
            if status:
                better = (
                    top_status is None
                    or status_rank.get(status, 0) > status_rank.get(top_status, 0)
                    or (
                        status_rank.get(status, 0) == status_rank.get(top_status, 0)
                        and prio > top_priority
                    )
                )
                if better:
                    top_status, top_reason, top_priority = status, reason, prio
        else:
            tb.end_rule(rule, False, rule["if"], {}, start_ns)

    # verdict: return only the fields rule authors set
    verdict_keys = {"decision_status", "reason", "final_status"}
    verdict = {k: v for k, v in enriched.items() if k in verdict_keys}

    # If we tracked top_status via precedence, override
    if top_status:
        verdict["decision_status"] = top_status
        if top_reason:
            verdict["reason"] = top_reason

    trace_json = tb.finalize(enriched)
    return verdict, trace_json
