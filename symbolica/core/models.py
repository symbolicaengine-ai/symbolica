"""
Symbolica Core Domain Models
============================

Simple, focused data structures for AI agent reasoning.
Optimized for deterministic execution and LLM explainability.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time


@dataclass(frozen=True)
class Rule:
    """Simple rule definition for AI agents."""
    id: str
    priority: int
    condition: str  # Expression string for AST evaluation
    actions: Dict[str, Any]  # Simple key-value actions
    tags: List[str] = field(default_factory=list)  # Rule metadata tags
    triggers: List[str] = field(default_factory=list)  # Rules to trigger after this one fires
    
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
        if not isinstance(self.triggers, list):
            raise ValueError("Triggers must be a list")


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
    """Result of rule execution for AI agents with simple explainability."""
    verdict: Dict[str, Any]  # Final computed facts
    fired_rules: List[str]   # IDs of rules that fired
    execution_time_ms: float # Execution time
    reasoning: str           # Simple explanation for LLMs
    
    @property
    def success(self) -> bool:
        """True if execution completed successfully."""
        return True  # Errors raise exceptions
    
    def get_llm_context(self) -> Dict[str, Any]:
        """Get simple context for LLM prompt inclusion."""
        return {
            "rules_fired": self.fired_rules,
            "final_facts": self.verdict,
            "execution_time_ms": self.execution_time_ms,
            "reasoning": self.reasoning
        }
    
    def get_reasoning_json(self) -> str:
        """Get JSON string for LLM prompt inclusion."""
        import json
        return json.dumps(self.get_llm_context(), indent=2)


@dataclass
class ExecutionContext:
    """Mutable execution context during rule processing."""
    original_facts: Facts
    enriched_facts: Dict[str, Any]
    fired_rules: List[str]
    reasoning_steps: List[str] = field(default_factory=list)
    _verdict: Dict[str, Any] = field(default_factory=dict)  # Track changes incrementally
    start_time: float = field(default_factory=time.perf_counter)
    
    def __post_init__(self):
        # Initialize enriched facts from original
        if not self.enriched_facts:
            self.enriched_facts = self.original_facts.data.copy()
    
    def set_fact(self, key: str, value: Any) -> None:
        """Set a fact in the context and track in verdict."""
        self.enriched_facts[key] = value
        # Track as changed if it's new or different from original
        if key not in self.original_facts.data or self.original_facts.data[key] != value:
            self._verdict[key] = value
    
    def get_fact(self, key: str, default: Any = None) -> Any:
        """Get a fact from the context."""
        return self.enriched_facts.get(key, default)
    
    def rule_fired(self, rule_id: str, reason: str, triggered_by: Optional[str] = None) -> None:
        """Record that a rule fired with simple reasoning."""
        self.fired_rules.append(rule_id)
        if triggered_by:
            self.reasoning_steps.append(f"✓ {rule_id}: {reason} (triggered by {triggered_by})")
        else:
            self.reasoning_steps.append(f"✓ {rule_id}: {reason}")
    
    @property
    def verdict(self) -> Dict[str, Any]:
        """Get verdict - facts that were added/modified."""
        return self._verdict.copy()
    
    @property
    def reasoning(self) -> str:
        """Get simple reasoning explanation."""
        if not self.reasoning_steps:
            return "No rules fired"
        return "\n".join(self.reasoning_steps)


@dataclass(frozen=True)
class Goal:
    """Simple goal data container - field-value pairs we want to achieve."""
    target: Dict[str, Any]
    
    def __post_init__(self):
        if not isinstance(self.target, dict) or not self.target:
            raise ValueError("Goal target must be a non-empty dictionary")





# Simple factory functions
def facts(**data: Any) -> Facts:
    """Create Facts from keyword arguments."""
    return Facts(data)

def goal(**target: Any) -> Goal:
    """Create Goal from keyword arguments."""
    return Goal(target) 