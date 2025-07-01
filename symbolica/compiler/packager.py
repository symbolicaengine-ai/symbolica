"""
symbolica.compiler.packager
===========================

Turn a folder of YAML rule files into a single *rulepack.rpack*.

Current v1 format (UTF-8 JSON):

{
  "header": {
      "version": "1",
      "built":   "2025-07-01T14:33:00Z",
      "status_precedence": ["REJECTED","ESCALATE","PARTIAL","APPROVED"],
      "agents": { "Default": [0,1,2], "DriverVerifier": [1,2] },
      "predicate_index": { "driver_listed_on_policy": [1], "state": [0,2] }
  },
  "rules": [
      { id:"timing.late", priority:80, agent:"Default", if:..., then:{set:{...}}},
      ...
  ]
}

Future versions can move to a binary mmap layout without changing these keys.
"""

from __future__ import annotations

import datetime as _dt
import json
import pathlib
from typing import Any, Dict, List, Sequence

import yaml

from .optimiser import optimise

# ---------------------------------------------------------------- constants
_MANDATORY_KEYS = ("id", "if", "then")


# ---------------------------------------------------------------- YAML loader
def _load_rules(rules_dir: str | pathlib.Path) -> List[Dict[str, Any]]:
    """Walk *rules_dir* and parse every *.yaml into a list of rule dicts."""
    rules: List[Dict[str, Any]] = []
    for path in pathlib.Path(rules_dir).rglob("*.yaml"):
        doc = yaml.safe_load(path.read_text())
        docs = doc if isinstance(doc, list) else [doc]

        for block in docs:
            rule = block.get("rule", {})
            # minimal schema check
            if not all(k in rule for k in _MANDATORY_KEYS):
                rid = rule.get("id", "?")
                raise ValueError(f"{path}: rule '{rid}' missing mandatory keys")

            rule.setdefault("priority", 50)
            rule.setdefault("agent", "Default")
            rules.append(rule)

    return rules


# ---------------------------------------------------------------- pack builder
def build_pack(
    rules_dir: str | pathlib.Path = "symbolica_rules",
    output_path: str | pathlib.Path = "rulepack.rpack",
    status_precedence: Sequence[str] | None = None,
) -> None:
    """
    Compile YAML rules into *output_path*.

    Parameters
    ----------
    rules_dir:
        Folder containing YAML rule files.
    output_path:
        Destination `.rpack` file (overwritten).
    status_precedence:
        Optional custom decision ladder; falls back to default list.
    """
    raw_rules = _load_rules(rules_dir)
    sorted_rules, predicate_index = optimise(raw_rules)

    # agent → list[int]  (indices in sorted_rules)
    agents: Dict[str, List[int]] = {}
    for idx, rule in enumerate(sorted_rules):
        agents.setdefault(rule["agent"], []).append(idx)

    header = {
        "version": "1",
        "built": _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "status_precedence": list(
            status_precedence
            or ["REJECTED", "ESCALATE", "PARTIAL", "APPROVED"]
        ),
        "agents": agents,
        "predicate_index": predicate_index,
    }

    pack = {"header": header, "rules": sorted_rules}
    out_path = pathlib.Path(output_path)
    out_path.write_text(json.dumps(pack, ensure_ascii=False))

    print(f"✔ rulepack written → {out_path}  ({len(sorted_rules)} rules)")
