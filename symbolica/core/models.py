"""
Symbolica Core Domain Models
============================

Immutable, well-defined data structures representing the business domain.
No dependencies on infrastructure - pure domain logic.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, FrozenSet
from enum import Enum
import time
import uuid
import hashlib


@dataclass(frozen=True)
class RuleId:
    """Strongly typed rule identifier."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError(f"Rule ID must be non-empty string: {self.value}")
        # Simple validation - alphanumeric, dots, underscores, hyphens
        if not all(c.isalnum() or c in '._-' for c in self.value):
            raise ValueError(f"Rule ID contains invalid characters: {self.value}")


@dataclass(frozen=True)
class Priority:
    """Rule execution priority with ordering."""
    value: int
    
    def __post_init__(self):
        if not isinstance(self.value, int) or self.value < 0:
            raise ValueError(f"Priority must be non-negative integer: {self.value}")
    
    def __lt__(self, other: 'Priority') -> bool:
        return self.value < other.value
    
    def __gt__(self, other: 'Priority') -> bool:
        return self.value > other.value


@dataclass(frozen=True)
class Condition:
    """Rule condition with content-based equality."""
    expression: str
    referenced_fields: FrozenSet[str] = field(init=False)
    content_hash: str = field(init=False)
    
    def __post_init__(self):
        if not self.expression or not isinstance(self.expression, str):
            raise ValueError("Condition expression must be non-empty string")
        
        # Extract fields (will be computed by parser)
        object.__setattr__(self, 'referenced_fields', frozenset())
        
        # Content-based hash for caching
        content = self.expression.strip()
        object.__setattr__(self, 'content_hash', 
                          hashlib.md5(content.encode()).hexdigest())


@dataclass(frozen=True)
class Action:
    """Single rule action."""
    type: str
    parameters: Dict[str, Any]
    
    def __post_init__(self):
        if not self.type:
            raise ValueError("Action type cannot be empty")
        if not isinstance(self.parameters, dict):
            raise ValueError("Action parameters must be a dictionary")


@dataclass(frozen=True)
class Rule:
    """Immutable rule definition."""
    id: RuleId
    priority: Priority
    condition: Condition
    actions: List[Action]
    tags: FrozenSet[str] = field(default_factory=frozenset)
    
    def __post_init__(self):
        if not self.actions:
            raise ValueError("Rule must have at least one action")
        
        # Ensure tags are frozen
        if not isinstance(self.tags, frozenset):
            object.__setattr__(self, 'tags', frozenset(self.tags or []))
    
    @property
    def referenced_fields(self) -> FrozenSet[str]:
        """Fields referenced by this rule's condition."""
        return self.condition.referenced_fields
    
    @property
    def written_fields(self) -> FrozenSet[str]:
        """Fields written by this rule's actions."""
        fields = set()
        for action in self.actions:
            if action.type == 'set':
                fields.update(action.parameters.keys())
        return frozenset(fields)


@dataclass(frozen=True)
class Facts:
    """Immutable facts container with fast lookups."""
    data: Dict[str, Any]
    content_hash: str = field(init=False)
    
    def __post_init__(self):
        if not isinstance(self.data, dict):
            raise ValueError("Facts data must be a dictionary")
        
        # Create content hash for caching
        content = str(sorted(self.data.items()))
        object.__setattr__(self, 'content_hash', 
                          hashlib.md5(content.encode()).hexdigest())
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get fact value with default."""
        return self.data.get(key, default)
    
    def has(self, key: str) -> bool:
        """Check if fact exists."""
        return key in self.data
    
    def __contains__(self, key: str) -> bool:
        return key in self.data
    
    def __getitem__(self, key: str) -> Any:
        return self.data[key]


@dataclass(frozen=True)
class ExecutionResult:
    """Immutable execution result."""
    verdict: Dict[str, Any]
    fired_rules: List[RuleId]
    execution_time_ns: int
    context_id: str
    
    @property
    def execution_time_ms(self) -> float:
        """Execution time in milliseconds."""
        return self.execution_time_ns / 1_000_000
    
    @property
    def success(self) -> bool:
        """True if execution completed successfully."""
        return True  # Errors raise exceptions
    
    @property
    def has_verdict(self) -> bool:
        """True if any rules fired and produced output."""
        return bool(self.verdict)
    
    def get_verdict(self, key: str, default: Any = None) -> Any:
        """Get verdict value with default."""
        return self.verdict.get(key, default)


class TraceLevel(Enum):
    """Trace detail levels for debugging."""
    NONE = "none"
    BASIC = "basic"
    DETAILED = "detailed"
    DEBUG = "debug"


@dataclass
class ExecutionContext:
    """Mutable execution context - encapsulates state during execution."""
    original_facts: Facts
    enriched_facts: Dict[str, Any]
    fired_rules: List[RuleId]
    trace_level: TraceLevel
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time_ns: int = field(default_factory=time.perf_counter_ns)
    
    def __post_init__(self):
        # Initialize enriched facts from original
        if not self.enriched_facts:
            self.enriched_facts = self.original_facts.data.copy()
    
    def set_fact(self, key: str, value: Any) -> None:
        """Set enriched fact."""
        self.enriched_facts[key] = value
    
    def get_fact(self, key: str, default: Any = None) -> Any:
        """Get fact from enriched facts."""
        return self.enriched_facts.get(key, default)
    
    def rule_fired(self, rule_id: RuleId) -> None:
        """Record that a rule fired."""
        self.fired_rules.append(rule_id)
    
    @property
    def execution_time_ns(self) -> int:
        """Current execution time in nanoseconds."""
        return time.perf_counter_ns() - self.start_time_ns
    
    @property
    def verdict(self) -> Dict[str, Any]:
        """Extract verdict - only facts that were added/modified."""
        return {k: v for k, v in self.enriched_facts.items() 
                if k not in self.original_facts.data or 
                self.original_facts.data[k] != v}


@dataclass(frozen=True)
class RuleSet:
    """Immutable collection of rules with metadata."""
    rules: List[Rule]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Validate no duplicate rule IDs
        ids = [rule.id.value for rule in self.rules]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            raise ValueError(f"Duplicate rule IDs: {duplicates}")
    
    @property
    def rule_count(self) -> int:
        """Number of rules in this set."""
        return len(self.rules)
    
    @property
    def rule_ids(self) -> List[str]:
        """List of all rule IDs."""
        return [rule.id.value for rule in self.rules]
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get rule by ID."""
        for rule in self.rules:
            if rule.id.value == rule_id:
                return rule
        return None
    
    def with_metadata(self, **metadata: Any) -> 'RuleSet':
        """Create new RuleSet with additional metadata."""
        new_metadata = {**self.metadata, **metadata}
        return RuleSet(self.rules, new_metadata)


# Factory functions for easy construction
def rule_id(value: str) -> RuleId:
    """Create RuleId."""
    return RuleId(value)


def priority(value: int) -> Priority:
    """Create Priority."""
    return Priority(value)


def condition(expression: str) -> Condition:
    """Create Condition."""
    return Condition(expression)


def action_set(**values: Any) -> Action:
    """Create set action."""
    return Action("set", values)


def action_call(function: str, **params: Any) -> Action:
    """Create call action."""
    return Action("call", {"function": function, "params": params})


def facts(**data: Any) -> Facts:
    """Create Facts."""
    return Facts(data) 