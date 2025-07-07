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
class FieldAccess:
    """Records field access during rule evaluation."""
    field_name: str
    value: Any
    access_type: str  # 'read' or 'write'
    rule_id: Optional[str] = None
    timestamp_ns: int = field(default_factory=time.perf_counter_ns)


@dataclass(frozen=True)
class ConditionTrace:
    """Detailed trace of condition evaluation."""
    expression: str
    result: bool
    evaluation_time_ns: int
    field_accesses: List[FieldAccess]
    error: Optional[str] = None
    
    def explain(self) -> str:
        """Generate human-readable explanation of condition evaluation."""
        if self.error:
            return f"Condition '{self.expression}' failed to evaluate: {self.error}"
        
        fields_used = [f"'{fa.field_name}' (= {fa.value})" for fa in self.field_accesses if fa.access_type == 'read']
        fields_str = ", ".join(fields_used) if fields_used else "no fields"
        
        result_str = "TRUE" if self.result else "FALSE"
        return f"Condition '{self.expression}' evaluated to {result_str} using fields: {fields_str}"


@dataclass(frozen=True)
class RuleEvaluationTrace:
    """Comprehensive trace of a single rule's evaluation."""
    rule_id: str
    priority: int
    condition_trace: ConditionTrace
    fired: bool
    actions_applied: Dict[str, Any]
    field_changes: List[FieldAccess]
    execution_time_ns: int
    tags: List[str] = field(default_factory=list)
    
    def explain(self) -> str:
        """Generate human-readable explanation of rule evaluation."""
        if not self.fired:
            return f"Rule '{self.rule_id}' (priority {self.priority}) did not fire because: {self.condition_trace.explain()}"
        
        actions_str = ", ".join([f"{k} = {v}" for k, v in self.actions_applied.items()])
        return f"Rule '{self.rule_id}' (priority {self.priority}) fired and set: {actions_str}. Reason: {self.condition_trace.explain()}"
    
    def get_reasoning_chain(self) -> Dict[str, Any]:
        """Get structured reasoning chain for LLM consumption."""
        return {
            "rule_id": self.rule_id,
            "priority": self.priority,
            "fired": self.fired,
            "condition": {
                "expression": self.condition_trace.expression,
                "result": self.condition_trace.result,
                "explanation": self.condition_trace.explain()
            },
            "actions": self.actions_applied if self.fired else {},
            "reasoning": self.explain(),
            "tags": self.tags
        }


@dataclass(frozen=True)
class ExecutionResult:
    """Result of rule execution for AI agents with detailed traceability."""
    verdict: Dict[str, Any]  # Final computed facts
    fired_rules: List[str]   # IDs of rules that fired
    execution_time_ms: float # Execution time
    trace: Dict[str, Any]    # Simple trace for AI explainability
    rule_traces: List[RuleEvaluationTrace] = field(default_factory=list)  # Detailed rule traces
    
    @property
    def success(self) -> bool:
        """True if execution completed successfully."""
        return True  # Errors raise exceptions
    
    def explain_reasoning(self) -> str:
        """Generate comprehensive explanation of the reasoning process."""
        explanations = []
        
        explanations.append(f"Engine evaluated {len(self.rule_traces)} rules in {self.execution_time_ms:.2f}ms")
        explanations.append(f"{len(self.fired_rules)} rules fired, resulting in {len(self.verdict)} final facts")
        
        if self.fired_rules:
            explanations.append("\nDetailed reasoning:")
            for rule_trace in self.rule_traces:
                if rule_trace.fired:
                    explanations.append(f"  ✓ {rule_trace.explain()}")
        
        non_fired_rules = [rt for rt in self.rule_traces if not rt.fired]
        if non_fired_rules:
            explanations.append(f"\n{len(non_fired_rules)} rules did not fire:")
            for rule_trace in non_fired_rules[:3]:  # Show first 3 for brevity
                explanations.append(f"  ✗ {rule_trace.explain()}")
            if len(non_fired_rules) > 3:
                explanations.append(f"  ... and {len(non_fired_rules) - 3} more")
        
        return "\n".join(explanations)
    
    def get_llm_context(self) -> Dict[str, Any]:
        """Get structured context for LLM prompt inclusion."""
        return {
            "reasoning_summary": {
                "total_rules_evaluated": len(self.rule_traces),
                "rules_fired": len(self.fired_rules),
                "execution_time_ms": self.execution_time_ms,
                "final_facts": self.verdict
            },
            "decision_chain": [rt.get_reasoning_chain() for rt in self.rule_traces if rt.fired],
            "rules_not_triggered": [
                {
                    "rule_id": rt.rule_id,
                    "reason": rt.condition_trace.explain(),
                    "tags": rt.tags
                }
                for rt in self.rule_traces if not rt.fired
            ][:5],  # Limit for prompt size
            "explanation": self.explain_reasoning()
        }
    
    def get_reasoning_json(self) -> str:
        """Get JSON string for LLM prompt inclusion."""
        import json
        return json.dumps(self.get_llm_context(), indent=2)


class TraceLevel(Enum):
    """Trace detail levels."""
    NONE = "none"
    BASIC = "basic"
    DETAILED = "detailed"


@dataclass
class ExecutionContext:
    """Mutable execution context during rule processing with detailed tracing."""
    original_facts: Facts
    enriched_facts: Dict[str, Any]
    fired_rules: List[str]
    trace_level: TraceLevel = TraceLevel.DETAILED  # Default to detailed for better explanations
    context_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    start_time_ns: int = field(default_factory=time.perf_counter_ns)
    
    # Enhanced tracing fields
    rule_traces: List[RuleEvaluationTrace] = field(default_factory=list)
    field_accesses: List[FieldAccess] = field(default_factory=list)
    current_rule_id: Optional[str] = None
    
    def __post_init__(self):
        # Initialize enriched facts from original
        if not self.enriched_facts:
            self.enriched_facts = self.original_facts.data.copy()
    
    def set_fact(self, key: str, value: Any) -> None:
        """Set a fact in the context with tracing."""
        old_value = self.enriched_facts.get(key)
        self.enriched_facts[key] = value
        
        # Record field access
        field_access = FieldAccess(
            field_name=key,
            value=value,
            access_type='write',
            rule_id=self.current_rule_id
        )
        self.field_accesses.append(field_access)
    
    def get_fact(self, key: str, default: Any = None) -> Any:
        """Get a fact from the context with tracing."""
        value = self.enriched_facts.get(key, default)
        
        # Record field access if we're in detailed tracing mode
        if self.trace_level == TraceLevel.DETAILED and key in self.enriched_facts:
            field_access = FieldAccess(
                field_name=key,
                value=value,
                access_type='read',
                rule_id=self.current_rule_id
            )
            self.field_accesses.append(field_access)
        
        return value
    
    def rule_fired(self, rule_id: str) -> None:
        """Record that a rule fired."""
        self.fired_rules.append(rule_id)
    
    def start_rule_evaluation(self, rule_id: str) -> None:
        """Mark the start of rule evaluation for tracing."""
        self.current_rule_id = rule_id
    
    def add_rule_trace(self, rule_trace: RuleEvaluationTrace) -> None:
        """Add a rule evaluation trace."""
        self.rule_traces.append(rule_trace)
    
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