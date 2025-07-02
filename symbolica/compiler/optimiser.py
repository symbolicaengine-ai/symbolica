"""
symbolica.compiler.optimiser
============================

Transforms the raw rule list into:

1. A priority-sorted DAG (simply a Python list for now).
2. A *predicate index* mapping each fact-field that appears in any
   leaf predicate to the positions in the DAG where it occurs.

API
---
    sorted_rules, pred_index = optimise(raw_rules)
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Sequence, Tuple


# ---------------------------------------------------------------- field harvest helpers
_FIELD_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_\.]*)\b")

def _collect_fields(cond: object) -> List[str]:
    """Recursively collect field names from the rule's *if:* condition."""
    fields: List[str] = []
    if isinstance(cond, str):
        # naive scan: grab identifiers that are not keywords
        for name in _FIELD_RE.findall(cond):
            if name not in {"and", "or", "not", "in"}:
                fields.append(name)
    elif isinstance(cond, dict):
        if "all" in cond or "any" in cond:
            for sub in cond.get("all", []) + cond.get("any", []):
                fields.extend(_collect_fields(sub))
        elif "not" in cond:
            fields.extend(_collect_fields(cond["not"]))
    return fields


# ---------------------------------------------------------------- main optimise() func
def optimise(
    raw_rules: Sequence[dict],
) -> Tuple[List[dict], Dict[str, List[int]]]:
    """
    Return (priority_sorted_rules, predicate_index).

    *priority_sorted_rules* is a **new list** sorted by:
        1. rule["priority"]  (default 50)  – DESC
        2. original sequence order         – stable tie-break

    *predicate_index* maps field name -> list[int]  (indices into the
    sorted list).  The index keeps the same order as the DAG so that
    evaluators can still respect priority when using the candidate set.
    """
    # attach _original_idx for stable sort
    sortable: List[dict] = []
    for idx, rule in enumerate(raw_rules):
        rule = dict(rule)                 # shallow copy
        rule["_original_idx"] = idx
        rule.setdefault("priority", 50)
        sortable.append(rule)

    # ❶ sort
    sortable.sort(
        key=lambda r: (-r["priority"], r["_original_idx"])
    )

    # ❷ build predicate index
    pred_index: Dict[str, List[int]] = defaultdict(list)
    for pos, rule in enumerate(sortable):
        fields = _collect_fields(rule["if"])
        for f in set(fields):             # dedupe within rule
            pred_index[f].append(pos)

    # drop helper key
    for r in sortable:
        r.pop("_original_idx", None)

    return sortable, dict(pred_index)
