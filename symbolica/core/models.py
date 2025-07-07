"""
Symbolica Core Domain Models
============================

Simple, focused data structures for AI agent reasoning.
Optimized for deterministic execution and traceability.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum
import time
import uuid


@dataclass(frozen=True)
class Rule:
    """Simple rule definition for AI agents."""
    id: str
    priority: int
    condition: str  # Expression string for AST evaluation
    actions: Dict[str, Any]  # Simple key-value actions
    tags: List[str] = field(default_factory=list)  # Rule metadata tags
    
    def __post_init__(self):
        if not self.id or not isinstance(self.id, str):
            raise ValueError("Rule ID must be a non-empty string")
        if not isinstance(self.priority, int):
            raise ValueError("Priority must be an integer")
        if not self.condition or not isinstance(self.condition, str):
            raise ValueError("Condition must be a non-empty string")
        if not isinstance(self.actions, dict) or not self.actions:
            raise ValueError("Actions must be a non-empty dictionary")
        if not isinstance(self.tags, list):
            raise ValueError("Tags must be a list")


@dataclass(frozen=True)
class Facts:
    """Immutable facts container."""
    data: Dict[str, Any]
    
    def __post_init__(self):
        if not isinstance(self.data, dict):
            raise ValueError("Facts data must be a dictionary")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get fact value with default."""
        return self.data.get(key, default)
    
    def __contains__(self, key: str) -> bool:
        return key in self.data
    
    def __getitem__(self, key: str) -> Any:
        return self.data[key]


@dataclass(frozen=True)
class ExecutionResult:
    """Result of rule execution for AI agents."""
    verdict: Dict[str, Any]  # Final computed facts
    fired_rules: List[str]   # IDs of rules that fired
    execution_time_ms: float # Execution time
    trace: Dict[str, Any]    # Simple trace for AI explainability
    
    @property
    def success(self) -> bool:
        """True if execution completed successfully."""
        return True  # Errors raise exceptions


class TraceLevel(Enum):
    """Trace detail levels."""
    NONE = "none"
    BASIC = "basic"
    DETAILED = "detailed"


@dataclass
class ExecutionContext:
    """Mutable execution context during rule processing."""
    original_facts: Facts
    enriched_facts: Dict[str, Any]
    fired_rules: List[str]
    trace_level: TraceLevel = TraceLevel.NONE
    context_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    start_time_ns: int = field(default_factory=time.perf_counter_ns)
    
    def __post_init__(self):
        # Initialize enriched facts from original
        if not self.enriched_facts:
            self.enriched_facts = self.original_facts.data.copy()
    
    def set_fact(self, key: str, value: Any) -> None:
        """Set a fact in the context."""
        self.enriched_facts[key] = value
    
    def get_fact(self, key: str, default: Any = None) -> Any:
        """Get a fact from the context."""
        return self.enriched_facts.get(key, default)
    
    def rule_fired(self, rule_id: str) -> None:
        """Record that a rule fired."""
        self.fired_rules.append(rule_id)
    
    @property
    def execution_time_ns(self) -> int:
        """Current execution time in nanoseconds."""
        return time.perf_counter_ns() - self.start_time_ns
    
    @property
    def verdict(self) -> Dict[str, Any]:
        """Extract verdict - facts that were added/modified."""
        return {k: v for k, v in self.enriched_facts.items() 
                if k not in self.original_facts.data or 
                self.original_facts.data[k] != v}


# Simple factory functions
def facts(**data: Any) -> Facts:
    """Create Facts from keyword arguments."""
    return Facts(data) 