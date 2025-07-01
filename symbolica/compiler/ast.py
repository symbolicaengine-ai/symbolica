"""
symbolica.compiler.ast
======================

Minimal Abstract-Syntax-Tree implementation used by the compiler and
runtime.  Four node types are enough for a v1 rule language:

*  Pred(field, op, value)   – leaf comparison (driver_age > 25)
*  And([...])               – logical AND
*  Or([...])                – logical OR
*  Not(child)               – logical NOT

Each node exposes::

    evaluate(facts: dict, cache: dict[str, bool]) -> bool

The per-request *cache* avoids recomputing identical predicates.
"""
from __future__ import annotations

import operator
from typing import Any, Dict, List

# --------------------------------------------------------------- operators
_OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "in": lambda x, y: x in y,
    "not in": lambda x, y: x not in y,
}


# --------------------------------------------------------------- base node
class Expr:
    """Abstract base node."""

    __slots__ = ()

    def evaluate(self, facts: Dict[str, Any], cache: Dict[str, bool]) -> bool:  # noqa: D401
        """Return True/False given the *facts* dict."""
        raise NotImplementedError


# --------------------------------------------------------------- leaves
class Pred(Expr):
    """Leaf predicate:  <field> <op> <value>"""

    __slots__ = ("field", "op", "value", "_cache_key")

    def __init__(self, field: str, op: str, value: Any):
        self.field = field
        self.op = op
        self.value = value
        self._cache_key = f"{field}{op}{value!r}"

    # main work
    def evaluate(self, facts: Dict[str, Any], cache: Dict[str, bool]) -> bool:
        if self._cache_key not in cache:
            left = facts.get(self.field)
            cache[self._cache_key] = _OPS[self.op](left, self.value)
        return cache[self._cache_key]

    # repr / debug helpers
    def __repr__(self) -> str:  # pragma: no cover
        return f"<Pred {self.field} {self.op} {self.value!r}>"


# --------------------------------------------------------------- boolean nodes
class And(Expr):
    __slots__ = ("children",)

    def __init__(self, *children: Expr):
        self.children: List[Expr] = list(children)

    def evaluate(self, facts: Dict[str, Any], cache: Dict[str, bool]) -> bool:
        return all(ch.evaluate(facts, cache) for ch in self.children)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<And {self.children}>"


class Or(Expr):
    __slots__ = ("children",)

    def __init__(self, *children: Expr):
        self.children = list(children)

    def evaluate(self, facts: Dict[str, Any], cache: Dict[str, bool]) -> bool:
        return any(ch.evaluate(facts, cache) for ch in self.children)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Or {self.children}>"


class Not(Expr):
    __slots__ = ("child",)

    def __init__(self, child: Expr):
        self.child = child

    def evaluate(self, facts: Dict[str, Any], cache: Dict[str, bool]) -> bool:
        return not self.child.evaluate(facts, cache)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Not {self.child}>"
