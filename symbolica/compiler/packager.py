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
      "agents": { "Default": [0,1,2], "FraudDetector": [1,2] },
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

from .parser import parse_yaml_file
from .optimiser import optimise

# ---------------------------------------------------------------- constants
_MANDATORY_KEYS = ("id", "if", "then")


def _load_registry_files(rules_dir: pathlib.Path) -> Dict[str, List[str]]:
    """Load all .reg.yaml registry files to build agent-to-rules mapping."""
    agent_rules: Dict[str, List[str]] = {}
    
    # Look for registry files in the parent directory of rules_dir
    registry_dir = rules_dir.parent if rules_dir.name == "rules" else rules_dir
    
    for reg_file in registry_dir.rglob("*.reg.yaml"):
        try:
            with open(reg_file, 'r') as f:
                registry_data = yaml.safe_load(f)
                
            agent_name = registry_data.get("agent", "Default")
            rule_list = registry_data.get("rules", [])
            
            if agent_name and rule_list:
                agent_rules[agent_name] = rule_list
                
        except Exception as e:
            print(f"Warning: Could not load registry {reg_file}: {e}")
    
    return agent_rules


# ---------------------------------------------------------------- YAML loader
def _load_rules(rules_dir: str | pathlib.Path) -> List[Dict[str, Any]]:
    """Walk *rules_dir* and parse every *.yaml into a list of rule dicts."""
    rules: List[Dict[str, Any]] = []
    for path in pathlib.Path(rules_dir).rglob("*.yaml"):
        try:
            # Use our updated parser that handles both formats
            parsed_rules = parse_yaml_file(path)
            
            for raw_rule in parsed_rules:
                # Convert RawRule back to dict format expected by optimizer
                rule_dict = {
                    "id": raw_rule["id"],
                    "priority": raw_rule["priority"],
                    "agent": "Default",  # Rules are agent-independent
                    "if": raw_rule["if_"],
                    "then": raw_rule["then"],
                    "tags": raw_rule["tags"]
                }
                
                # Validate that we have the essential components
                if not all(k in rule_dict for k in ["id", "if", "then"]):
                    rid = rule_dict.get("id", "?")
                    raise ValueError(f"{path}: rule '{rid}' missing mandatory keys")
                
                rules.append(rule_dict)
                
        except Exception as e:
            # Provide helpful error context
            raise ValueError(f"Failed to parse {path}: {e}") from e

    return rules


def _build_agent_mapping(sorted_rules: List[Dict[str, Any]], 
                        agent_rules: Dict[str, List[str]]) -> Dict[str, List[int]]:
    """Build agent -> rule_indices mapping based on registry files."""
    # Create rule_id -> index mapping
    rule_id_to_index = {rule["id"]: idx for idx, rule in enumerate(sorted_rules)}
    
    # Build agent mappings based on registry files
    agents: Dict[str, List[int]] = {}
    
    for agent_name, rule_ids in agent_rules.items():
        agent_indices = []
        for rule_id in rule_ids:
            if rule_id in rule_id_to_index:
                agent_indices.append(rule_id_to_index[rule_id])
            else:
                print(f"Warning: Agent {agent_name} references unknown rule: {rule_id}")
        
        if agent_indices:
            agents[agent_name] = sorted(agent_indices)  # Keep priority order
    
    return agents


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
    rules_dir_path = pathlib.Path(rules_dir)
    
    # Load rules (now agent-independent)
    raw_rules = _load_rules(rules_dir_path)
    sorted_rules, predicate_index = optimise(raw_rules)

    # Load registry files to build agent mappings
    agent_rules = _load_registry_files(rules_dir_path)
    agents = _build_agent_mapping(sorted_rules, agent_rules)

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
    if agents:
        print(f"  Agent mappings: {list(agents.keys())}")
    else:
        print("  Warning: No registry files found - all rules available to all agents")
