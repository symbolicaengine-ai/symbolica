"""
symbolica.registry.globmatch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Helpers for applying **agent-registry include / exclude patterns** to
the full set of compiled rule-IDs.

* Patterns follow the same semantics as Unix shell globs (`fnmatch`):
  - `*`  matches any sequence of characters except the slash
  - `**` matches across path separators (if you choose to use `.` as a
    namespace separator inside rule IDs)
  - `?`  matches a single character

Example
-------
 filter_rules(
     rule_ids=["timing.late", "driver.not_listed", "coverage.limit"],
     includes=["driver.*", "timing.*"],
     excludes=["*.experimental"]
)
['timing.late', 'driver.not_listed']
"""

from __future__ import annotations

import fnmatch
from typing import Iterable, Sequence, List


def _compile_globs(patterns: Sequence[str] | None) -> list[str]:
    """Normalize a list of glob patterns; accept None as empty."""
    return list(patterns or [])


def _matches_any(name: str, patterns: list[str]) -> bool:
    """Return True if *name* matches **any** pattern in *patterns*."""
    return any(fnmatch.fnmatchcase(name, pat) for pat in patterns)


def filter_rules(
    rule_ids: Iterable[str],
    includes: Sequence[str] | None = None,
    excludes: Sequence[str] | None = None,
) -> List[str]:
    """
    Return a list of rule-IDs that survive the include / exclude filters.

    Parameters
    ----------
    rule_ids:
        All rule identifiers produced by the compiler.
    includes:
        Glob patterns that **must** match for a rule to be kept.
        If ``None`` or empty, the default is ``["*"]`` (everything).
    excludes:
        Glob patterns that, if matched, **remove** a rule. Evaluated *after*
        the include list.  If ``None`` or empty, nothing is excluded.

    Notes
    -----
    • Pattern matching is **case-sensitive** (`fnmatchcase`).  
    • Exclude patterns override includes if both match the same rule.

    Returns
    -------
    list[str]
        Rule-IDs that the agent should be allowed to see.
    """
    inc = _compile_globs(includes or ["*"])
    exc = _compile_globs(excludes)

    kept: list[str] = []
    for rid in rule_ids:
        if not _matches_any(rid, inc):
            continue  # didn’t pass include filter
        if exc and _matches_any(rid, exc):
            continue  # explicitly excluded
        kept.append(rid)
    return kept
