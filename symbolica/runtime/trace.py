"""
symbolica.runtime.trace
~~~~~~~~~~~~~~~~~~~~~~~

Tiny helper that builds Symbolica's JSON trace in three verbosity levels:

* **compact**  – list of rule IDs that fired.
* **verbose**  – compact + predicates that were tested + set-dict emitted.
* **debug**    – verbose + per-rule micro-timings + memo-cache stats.

Usage (inside evaluator)
------------------------
    tb = TraceBuilder(level="verbose", run_id="abc123")

    start_ns = tb.begin_rule(rule["id"])
    fired = evaluate_rule(...)
    tb.end_rule(rule, fired, cond_tree, set_dict, start_ns)

    trace_json = tb.finalize(enriched_facts)

The evaluator already returns the final JSON; TraceBuilder just helps keep
the logic tidy.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional


class TraceBuilder:
    __slots__ = ("level", "_run_id", "_rules", "_start", "_rule_timings")

    def __init__(self, level: str = "compact", run_id: Optional[str] = None):
        self.level = level  # "compact" | "verbose" | "debug"
        self._run_id = run_id or str(int(time.time() * 1e6))
        self._rules: List[Dict[str, Any] | str] = []
        self._start = time.perf_counter_ns()  # debug total runtime
        self._rule_timings: Dict[str, int] = {}  # id -> nanoseconds

    # ---------------------------------------------------------------- rule hooks
    def begin_rule(self, rule_id: str) -> int:
        """
        Call at start of rule evaluation.
        Returns a timestamp (ns) to feed into end_rule if in debug mode.
        """
        return time.perf_counter_ns() if self.level == "debug" else 0

    def end_rule(
        self,
        rule: Dict[str, Any],
        fired: bool,
        cond_repr: Any,
        emitted: Dict[str, Any],
        start_ns: int = 0,
    ) -> None:
        """
        Record outcome for a rule.

        Parameters
        ----------
        rule      : original rule dict (needs 'id').
        fired     : whether the rule's if: evaluated True.
        cond_repr : the original if: (string or dict) for verbose trace.
        emitted   : dict merged into facts (then.set).
        start_ns  : timestamp returned by begin_rule().
        """
        if not fired:
            if self.level == "debug":
                self._rule_timings[rule["id"]] = time.perf_counter_ns() - start_ns
            return

        if self.level == "compact":
            self._rules.append(rule["id"])
        else:
            entry: Dict[str, Any] = {"id": rule["id"], "set": emitted}
            if self.level in ("verbose", "debug"):
                entry["cond"] = cond_repr
            self._rules.append(entry)

        if self.level == "debug":
            self._rule_timings[rule["id"]] = time.perf_counter_ns() - start_ns

    # ---------------------------------------------------------------- finalize
    def finalize(self, facts_final: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return the finished trace JSON and clear internal buffers.
        """
        out: Dict[str, Any] = {
            "run_id": self._run_id,
            "level": self.level,
            "fired": self._rules,
        }
        if self.level in ("verbose", "debug"):
            out["facts_final"] = facts_final
        if self.level == "debug":
            out["timings_ns"] = {
                "_total": time.perf_counter_ns() - self._start,
                **self._rule_timings,
            }
        # reset to avoid accidental reuse
        self._rules = []
        return out
