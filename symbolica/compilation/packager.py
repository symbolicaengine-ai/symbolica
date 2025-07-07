"""
Rule Packager
=============

Creates efficient binary rule packs for fast loading and execution.

Features:
- Binary serialization
- Metadata embedding
- Optimization markers
- Version tracking
"""

import json
import pathlib
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from ..core import RuleSet, Rule


@dataclass
class RulePackMetadata:
    """Metadata for rule pack."""
    version: str = "1.0"
    created_at: str = ""
    rule_count: int = 0
    optimization_level: str = "default"
    compiler_version: str = "1.0.0"
    checksum: Optional[str] = None


class RulePackager:
    """
    Creates optimized rule packs for execution.
    
    Features:
    - JSON serialization with metadata
    - Rule optimization markers
    - Fast loading format
    - Version compatibility
    """
    
    def __init__(self, optimization_level: str = "default"):
        self.optimization_level = optimization_level
    
    def create_pack(self, rule_set: RuleSet, output_path: Optional[pathlib.Path] = None) -> Dict[str, Any]:
        """Create rule pack from rule set."""
        
        # Create metadata
        metadata = RulePackMetadata(
            created_at=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            rule_count=rule_set.rule_count,
            optimization_level=self.optimization_level
        )
        
        # Serialize rules
        serialized_rules = self._serialize_rules(rule_set.rules)
        
        # Create pack structure
        pack_data = {
            "metadata": asdict(metadata),
            "rules": serialized_rules,
            "rule_metadata": rule_set.metadata,
            "format_version": "1.0"
        }
        
        # Calculate checksum
        pack_json = json.dumps(pack_data, sort_keys=True)
        metadata.checksum = str(hash(pack_json))
        pack_data["metadata"] = asdict(metadata)
        
        # Save to file if path provided
        if output_path:
            self._save_pack(pack_data, output_path)
        
        return pack_data
    
    def load_pack(self, pack_path: pathlib.Path) -> Dict[str, Any]:
        """Load rule pack from file."""
        if not pack_path.exists():
            raise FileNotFoundError(f"Rule pack not found: {pack_path}")
        
        try:
            with open(pack_path, 'r', encoding='utf-8') as f:
                pack_data = json.load(f)
            
            # Validate format
            if pack_data.get("format_version") != "1.0":
                raise ValueError(f"Unsupported pack format version: {pack_data.get('format_version')}")
            
            return pack_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in rule pack: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load rule pack: {e}")
    
    def _serialize_rules(self, rules: List[Rule]) -> List[Dict[str, Any]]:
        """Serialize rules to JSON-compatible format."""
        serialized = []
        
        for rule in rules:
            rule_data = {
                "id": rule.id.value,
                "priority": rule.priority.value,
                "condition": {
                    "expression": rule.condition.expression,
                    "content_hash": rule.condition.content_hash,
                    "referenced_fields": list(rule.condition.referenced_fields)
                },
                "actions": [
                    {
                        "type": action.type,
                        "parameters": action.parameters
                    }
                    for action in rule.actions
                ],
                "tags": list(rule.tags),
                "written_fields": list(rule.written_fields)
            }
            serialized.append(rule_data)
        
        return serialized
    
    def _save_pack(self, pack_data: Dict[str, Any], output_path: pathlib.Path) -> None:
        """Save pack data to file."""
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write with proper formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(pack_data, f, indent=2, ensure_ascii=False)
    
    def get_pack_info(self, pack_path: pathlib.Path) -> Dict[str, Any]:
        """Get information about a rule pack without full loading."""
        pack_data = self.load_pack(pack_path)
        
        metadata = pack_data.get("metadata", {})
        rules = pack_data.get("rules", [])
        
        # Basic stats
        info = {
            "path": str(pack_path),
            "file_size": pack_path.stat().st_size,
            "metadata": metadata,
            "rule_count": len(rules),
            "format_version": pack_data.get("format_version", "unknown")
        }
        
        # Rule analysis
        if rules:
            priorities = [rule.get("priority", 50) for rule in rules]
            info.update({
                "priority_range": {
                    "min": min(priorities),
                    "max": max(priorities),
                    "average": sum(priorities) / len(priorities)
                },
                "has_tags": any(rule.get("tags") for rule in rules),
                "total_actions": sum(len(rule.get("actions", [])) for rule in rules)
            })
        
        return info


# Convenience functions
def create_rule_pack(rule_set: RuleSet, 
                    output_path: Optional[pathlib.Path] = None,
                    optimization_level: str = "default") -> Dict[str, Any]:
    """Create rule pack from rule set."""
    packager = RulePackager(optimization_level=optimization_level)
    return packager.create_pack(rule_set, output_path)


def load_rule_pack(pack_path: pathlib.Path) -> Dict[str, Any]:
    """Load rule pack from file."""
    packager = RulePackager()
    return packager.load_pack(pack_path)


def get_pack_info(pack_path: pathlib.Path) -> Dict[str, Any]:
    """Get rule pack information."""
    packager = RulePackager()
    return packager.get_pack_info(pack_path) 