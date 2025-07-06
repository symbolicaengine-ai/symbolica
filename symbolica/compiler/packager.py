"""
symbolica.compiler.packager
============================

Build .rpack files (Symbolica's bytecode format).

Current DAG-enabled format (UTF-8 JSON with ExecutionDAG):
    {
        "header": {"built": "...", "version": "dag", "execution_dag": {...}},
        "rules": [...],
        "agents": {...}
    }

Legacy format (UTF-8 JSON without DAG):
    {
        "header": {"built": "...", "version": "legacy"},
        "rules": [...],
        "agents": {...}
    }

.rpack files are gzip-compressed JSON for compactness and faster loading.
"""

from __future__ import annotations

import datetime as _dt
import json
import pathlib
from typing import Any, Dict, List, Sequence
import yaml

from .parser import parse_yaml_file
from .optimiser import optimise

# Import DAG builder for enhanced features
try:
    from .dag import build_execution_dag, ExecutionDAG
    DAG_AVAILABLE = True
except ImportError:
    DAG_AVAILABLE = False
    def build_execution_dag(rules):
        return None

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


def _load_rules(rules_dir_path: pathlib.Path) -> List[Dict[str, Any]]:
    """Load all YAML rule files from the rules directory."""
    
    rules = []
    for yaml_file in rules_dir_path.rglob("*.yaml"):
        if yaml_file.name.endswith(".reg.yaml"):
            continue  # Skip registry files
            
        try:
            raw_rules = parse_yaml_file(yaml_file)
            
            # Handle both single rule and multi-rule YAML files
            if isinstance(raw_rules, list):
                for rule in raw_rules:
                    rules.append(_normalize_rule_format(rule))
            else:
                rules.append(_normalize_rule_format(raw_rules))
                
        except Exception as e:
            print(f"Warning: Could not parse {yaml_file}: {e}")
    
    # Validate required keys after normalization
    for rule in rules:
        for key in _MANDATORY_KEYS:
            if key not in rule:
                raise ValueError(f"Rule {rule.get('id', 'unknown')} missing key: {key}")
    
    return rules


def _normalize_rule_format(rule: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize rule format to standard if/then structure."""
    
    # Handle RawRule format (from parser)
    if "if_" in rule:
        normalized = {
            "id": rule["id"],
            "priority": rule.get("priority", 50),
            "if": rule["if_"],
            "then": rule["then"],
            "tags": rule.get("tags", [])
        }
        return normalized
    
    # Handle legacy conditions/actions format
    elif "conditions" in rule and "actions" in rule:
        # Convert conditions to if format
        conditions = rule["conditions"]
        if len(conditions) == 1:
            if_condition = conditions[0]
        else:
            if_condition = {"all": conditions}
        
        # Convert actions to then format
        actions = rule["actions"]
        then_actions = {}
        set_dict = {}
        
        for action in actions:
            if isinstance(action, dict):
                set_dict.update(action)
            else:
                set_dict["action"] = action
        
        if set_dict:
            then_actions["set"] = set_dict
        
        normalized = {
            "id": rule["id"],
            "priority": rule.get("priority", 50),
            "if": if_condition,
            "then": then_actions,
            "tags": rule.get("tags", [])
        }
        return normalized
    
    # Already in correct format
    else:
        return rule


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


def _serialize_execution_dag(execution_dag: 'ExecutionDAG') -> Dict[str, Any]:
    """Serialize ExecutionDAG for storage in .rpack file."""
    if not execution_dag:
        return {}
    
    # Serialize execution layers
    layers_data = []
    for layer in execution_dag.execution_layers:
        layers_data.append({
            "layer_id": layer.layer_id,
            "rules": layer.rules,
            "description": layer.description
        })
    
    # Serialize conflicts
    conflicts_data = []
    for conflict in execution_dag.conflicts:
        conflicts_data.append({
            "field": conflict.field,
            "rules": conflict.rules,
            "message": conflict.message,
            "resolvable": conflict.resolvable
        })
    
    # Serialize rule nodes (with simplified AST)
    rules_data = {}
    for rule_id, rule_node in execution_dag.rules.items():
        rules_data[rule_id] = {
            "id": rule_node.id,
            "priority": rule_node.priority,
            "reads": list(rule_node.reads),
            "writes": list(rule_node.writes),
            "dependencies": list(rule_node.dependencies),
            "dependents": list(rule_node.dependents),
            "actions": rule_node.actions,
            # Note: condition_ast is not serialized, will be reparsed at runtime
        }
    
    # Serialize field nodes  
    fields_data = {}
    for field_name, field_node in execution_dag.fields.items():
        fields_data[field_name] = {
            "id": field_node.id,
            "is_input": field_node.is_input,
            "producers": list(field_node.producers),
            "consumers": list(field_node.consumers),
            "dependencies": list(field_node.dependencies),
            "dependents": list(field_node.dependents)
        }
    
    return {
        "execution_layers": layers_data,
        "conflicts": conflicts_data,
        "rules": rules_data,
        "fields": fields_data,
        "input_fields": list(execution_dag.input_fields),
        "output_fields": list(execution_dag.output_fields),
        "parallel_opportunities": sum(len(layer.rules) for layer in execution_dag.execution_layers if len(layer.rules) > 1)
    }


# ---------------------------------------------------------------- pack builder
def build_pack(
    rules_dir: str | pathlib.Path = "symbolica_rules",
    output_path: str | pathlib.Path = "rulepack.rpack",
    status_precedence: Sequence[str] | None = None,
    enable_dag: bool = True,
) -> None:
    """
    Compile YAML rules into *output_path* with optional DAG support.

    Parameters
    ----------
    rules_dir:
        Folder containing YAML rule files.
    output_path:
        Destination `.rpack` file (overwritten).
    status_precedence:
        Optional custom decision ladder; falls back to default list.
    enable_dag:
        Enable DAG-based execution (default True).
    """
    rules_dir_path = pathlib.Path(rules_dir)
    
    # Load rules (now agent-independent)
    raw_rules = _load_rules(rules_dir_path)
    sorted_rules, predicate_index = optimise(raw_rules)

    # Load registry files to build agent mappings
    agent_rules = _load_registry_files(rules_dir_path)
    agents = _build_agent_mapping(sorted_rules, agent_rules)

    # Build ExecutionDAG if enabled
    execution_dag_data = {}
    dag_enabled = False
    
    if enable_dag and DAG_AVAILABLE:
        try:
            execution_dag = build_execution_dag(sorted_rules)
            execution_dag_data = _serialize_execution_dag(execution_dag)
            dag_enabled = True
            
            print(f"✔ DAG built: {len(execution_dag.execution_layers)} layers, {execution_dag_data.get('parallel_opportunities', 0)} parallel opportunities")
            
        except Exception as e:
            print(f"Warning: DAG build failed, falling back to legacy mode: {e}")
            dag_enabled = False

    # Determine version based on DAG availability
    version = "dag" if dag_enabled else "legacy"

    header = {
        "version": version,
        "built": _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "status_precedence": list(
            status_precedence
            or ["REJECTED", "ESCALATE", "PARTIAL", "APPROVED"]
        ),
        "agents": agents,
        "predicate_index": predicate_index,
        "dag_enabled": dag_enabled,
    }
    
    # Add DAG data if available
    if execution_dag_data:
        header["execution_dag"] = execution_dag_data

    pack = {"header": header, "rules": sorted_rules}
    out_path = pathlib.Path(output_path)
    out_path.write_text(json.dumps(pack, ensure_ascii=False))

    print(f"✔ rulepack written → {out_path}  ({len(sorted_rules)} rules, {version})")
    if agents:
        print(f"  Agent mappings: {list(agents.keys())}")
    else:
        print("  Warning: No registry files found - all rules available to all agents")
    
    if dag_enabled:
        print(f"  DAG: {len(execution_dag_data.get('execution_layers', []))} execution layers")
        conflicts = execution_dag_data.get('conflicts', [])
        if conflicts:
            resolvable = sum(1 for c in conflicts if c.get('resolvable', False))
            unresolvable = len(conflicts) - resolvable
            print(f"  Conflicts: {resolvable} resolvable, {unresolvable} unresolvable")


def build_pack_legacy(
    rules_dir: str | pathlib.Path = "symbolica_rules",
    output_path: str | pathlib.Path = "rulepack.rpack",
    status_precedence: Sequence[str] | None = None,
) -> None:
    """Build legacy pack without DAG features."""
    build_pack(rules_dir, output_path, status_precedence, enable_dag=False)


def build_pack_dag(
    rules_dir: str | pathlib.Path = "symbolica_rules", 
    output_path: str | pathlib.Path = "rulepack.rpack",
    status_precedence: Sequence[str] | None = None,
) -> None:
    """Build pack with DAG features enabled."""
    build_pack(rules_dir, output_path, status_precedence, enable_dag=True)


def get_pack_info(rpack_path: str | pathlib.Path) -> Dict[str, Any]:
    """Get information about a compiled .rpack file."""
    rpack_path = pathlib.Path(rpack_path)
    
    if not rpack_path.exists():
        raise FileNotFoundError(f"Rule pack not found: {rpack_path}")
    
    try:
        data = json.loads(rpack_path.read_text())
        header = data.get("header", {})
        rules = data.get("rules", [])
        
        info = {
            "path": str(rpack_path),
            "version": header.get("version", "unknown"),
            "built": header.get("built", "unknown"),
            "rule_count": len(rules),
            "agents": list(header.get("agents", {}).keys()),
            "dag_enabled": header.get("dag_enabled", False),
            "file_size": rpack_path.stat().st_size,
        }
        
        # Add DAG info if available
        if header.get("execution_dag"):
            dag_data = header["execution_dag"]
            info["dag_info"] = {
                "execution_layers": len(dag_data.get("execution_layers", [])),
                "conflicts": len(dag_data.get("conflicts", [])),
                "parallel_opportunities": dag_data.get("parallel_opportunities", 0),
                "input_fields": len(dag_data.get("input_fields", [])),
                "output_fields": len(dag_data.get("output_fields", []))
            }
        
        return info
        
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Invalid rule pack format: {e}")
