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
    actions: Dict[str, Any]  # Simple key-value actions (final outputs)
    facts: Dict[str, Any] = field(default_factory=dict)  # Intermediate state (shared between rules)
    tags: List[str] = field(default_factory=list)  # Rule metadata tags
    triggers: List[str] = field(default_factory=list)  # Rules to trigger after this one fires
    description: str = ""  # Optional description for documentation
    enabled: bool = True  # Whether rule is enabled
    
    def __post_init__(self):
        if not self.id or not isinstance(self.id, str):
            raise ValueError("Rule ID must be a non-empty string")
        if not isinstance(self.priority, int):
            raise ValueError("Priority must be an integer")
        if not self.condition or not isinstance(self.condition, str):
            raise ValueError("Condition must be a non-empty string")
        if not isinstance(self.actions, dict) or not self.actions:
            raise ValueError("Actions must be a non-empty dictionary")
        if not isinstance(self.facts, dict):
            raise ValueError("Facts must be a dictionary")
        if not isinstance(self.tags, list):
            raise ValueError("Tags must be a list")
        if not isinstance(self.triggers, list):
            raise ValueError("Triggers must be a list")
        if not isinstance(self.description, str):
            raise ValueError("Description must be a string")
        if not isinstance(self.enabled, bool):
            raise ValueError("Enabled must be a boolean")


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
    intermediate_facts: Dict[str, Any] = field(default_factory=dict)  # Facts created during execution
    _context: Optional['ExecutionContext'] = field(default=None, repr=False)  # Store context for rich tracing
    
    @property
    def success(self) -> bool:
        """True if execution completed successfully."""
        return True  # Errors raise exceptions
    
    def get_llm_context(self) -> Dict[str, Any]:
        """Get simple context for LLM prompt inclusion."""
        return {
            "rules_fired": self.fired_rules,
            "final_facts": self.verdict,
            "intermediate_facts": self.intermediate_facts,
            "execution_time_ms": self.execution_time_ms,
            "reasoning": self.reasoning
        }
    
    def get_hierarchical_reasoning(self) -> Dict[str, Any]:
        """Get rich hierarchical reasoning context for advanced LLM processing."""
        if self._context and hasattr(self._context, 'get_llm_reasoning_context'):
            return self._context.get_llm_reasoning_context()
        else:
            # Fallback to simple context
            return self.get_llm_context()
    
    def get_reasoning_json(self) -> str:
        """Get JSON string for LLM prompt inclusion."""
        import json
        return json.dumps(self.get_llm_context(), indent=2)
    
    def get_hierarchical_reasoning_json(self) -> str:
        """Get hierarchical reasoning as JSON for advanced LLM processing."""
        import json
        return json.dumps(self.get_hierarchical_reasoning(), indent=2)
    
    def explain_decision_path(self) -> str:
        """Generate a human-readable explanation of the decision path."""
        if not self._context:
            return self.reasoning
        
        llm_context = self.get_hierarchical_reasoning()
        reasoning_chain = llm_context.get('reasoning_chain', [])
        
        if not reasoning_chain:
            return self.reasoning
        
        explanation_parts = ["Decision path:"]
        
        for i, step in enumerate(reasoning_chain, 1):
            rule_id = step.get('rule_id', 'unknown')
            condition = step.get('condition', 'unknown condition')
            explanation = step.get('explanation', 'No explanation')
            time_ms = step.get('execution_time_ms', 0)
            
            explanation_parts.append(f"{i}. Rule '{rule_id}': {explanation}")
            if time_ms > 0:
                explanation_parts.append(f"   (evaluated in {time_ms:.2f}ms)")
        
        return "\n".join(explanation_parts)
    
    def get_critical_conditions(self) -> List[Dict[str, Any]]:
        """Get the critical conditions that led to the decision."""
        if not self._context:
            return []
        
        llm_context = self.get_hierarchical_reasoning()
        reasoning_chain = llm_context.get('reasoning_chain', [])
        
        critical_conditions = []
        for step in reasoning_chain:
            key_factors = step.get('key_factors', [])
            if key_factors:
                critical_conditions.append({
                    'rule_id': step.get('rule_id'),
                    'condition': step.get('condition'),
                    'key_factors': key_factors,
                    'result': step.get('result')
                })
        
        return critical_conditions


@dataclass(frozen=True)
class Goal:
    """Goal for backward chaining - what we want to achieve."""
    target_facts: Dict[str, Any]
    
    def __post_init__(self):
        if not isinstance(self.target_facts, dict):
            raise ValueError("Target facts must be a dictionary")
        if not self.target_facts:
            raise ValueError("Target facts cannot be empty")


def facts(**kwargs) -> Facts:
    """Factory function for creating Facts."""
    return Facts(kwargs)


def goal(**kwargs) -> Goal:
    """Factory function for creating Goals."""
    return Goal(kwargs)


@dataclass
class ExecutionContext:
    """Mutable execution context during rule processing."""
    original_facts: Facts
    enriched_facts: Dict[str, Any]
    fired_rules: List[str]
    reasoning_steps: List[str] = field(default_factory=list)
    _verdict: Dict[str, Any] = field(default_factory=dict)  # Track changes incrementally
    _verdict_priorities: Dict[str, int] = field(default_factory=dict)  # Track priority of rule that set each fact
    _intermediate_facts: Dict[str, Any] = field(default_factory=dict)  # Track facts created by rules
    start_time: float = field(default_factory=time.perf_counter)
    _rule_traces: Dict[str, Any] = field(default_factory=dict)  # Store hierarchical traces per rule
    
    def __post_init__(self):
        # Initialize enriched facts from original
        if not self.enriched_facts:
            self.enriched_facts = self.original_facts.data.copy()
    
    def set_fact(self, key: str, value: Any, priority: int = 0) -> None:
        """Set a fact in the context and track in verdict, considering rule priority."""
        self.enriched_facts[key] = value
        # Track as changed if it's new or different from original
        if key not in self.original_facts.data or self.original_facts.data[key] != value:
            # Only set in verdict if this rule has higher priority than the existing one
            existing_priority = self._verdict_priorities.get(key, -1)
            if priority >= existing_priority:
                self._verdict[key] = value
                self._verdict_priorities[key] = priority
    
    def set_intermediate_fact(self, key: str, value: Any) -> None:
        """Set an intermediate fact that other rules can use (but not in final verdict)."""
        self.enriched_facts[key] = value
        self._intermediate_facts[key] = value
    
    def get_fact(self, key: str, default: Any = None) -> Any:
        """Get a fact from the context."""
        return self.enriched_facts.get(key, default)
    
    def rule_fired(self, rule_id: str, reason: str, triggered_by: Optional[str] = None) -> None:
        """Record that a rule fired with simple reasoning."""
        self.fired_rules.append(rule_id)
        if triggered_by:
            self.reasoning_steps.append(f"{rule_id}: {reason} (triggered by {triggered_by})")
        else:
            self.reasoning_steps.append(f"{rule_id}: {reason}")
    
    def store_rule_trace(self, rule_id: str, execution_path: Any) -> None:
        """Store execution path for a rule."""
        self._rule_traces[rule_id] = execution_path
    
    def get_rule_trace(self, rule_id: str) -> Optional[Any]:
        """Get execution path for a rule."""
        return self._rule_traces.get(rule_id)
    
    def get_all_traces(self) -> Dict[str, Any]:
        """Get all stored execution paths."""
        return self._rule_traces.copy()
    
    def get_llm_reasoning_context(self) -> Dict[str, Any]:
        """Get rich reasoning context optimized for LLM processing."""
        traces_for_llm = {}
        for rule_id, execution_path in self._rule_traces.items():
            if hasattr(execution_path, 'get_llm_context'):
                traces_for_llm[rule_id] = execution_path.get_llm_context()
        
        return {
            'fired_rules': self.fired_rules,
            'rule_traces': traces_for_llm,
            'facts_added': self._verdict,
            'intermediate_facts': self._intermediate_facts,
            'execution_summary': {
                'rules_evaluated': len(self._rule_traces),
                'rules_fired': len(self.fired_rules),
                'facts_modified': len(self._verdict),
                'intermediate_facts_created': len(self._intermediate_facts),
                'total_execution_time_ms': (time.perf_counter() - self.start_time) * 1000
            },
            'reasoning_chain': self._build_reasoning_chain()
        }
    
    def _build_reasoning_chain(self) -> List[Dict[str, Any]]:
        """Build a structured reasoning chain for LLM consumption."""
        chain = []
        
        for rule_id in self.fired_rules:
            execution_path = self._rule_traces.get(rule_id)
            if execution_path and hasattr(execution_path, 'get_llm_context'):
                llm_context = execution_path.get_llm_context()
                chain.append({
                    'rule_id': rule_id,
                    'condition': llm_context.get('expression', 'unknown'),
                    'result': llm_context.get('result', False),
                    'explanation': llm_context.get('explanation', 'No explanation available'),
                    'key_factors': [step['explanation'] for step in llm_context.get('critical_path', [])],
                    'execution_time_ms': llm_context.get('total_time_ms', 0)
                })
            else:
                # Fallback for rules without execution paths
                reasoning_step = next((step for step in self.reasoning_steps if step.startswith(f"{rule_id}:")), "")
                chain.append({
                    'rule_id': rule_id,
                    'condition': 'unknown',
                    'result': True,  # Must be true if rule fired
                    'explanation': reasoning_step,
                    'key_factors': [],
                    'execution_time_ms': 0
                })
        
        return chain
    
    @property
    def verdict(self) -> Dict[str, Any]:
        """Get verdict - facts that were added/modified."""
        return self._verdict.copy()
    
    @property
    def intermediate_facts(self) -> Dict[str, Any]:
        """Get intermediate facts created during execution."""
        return self._intermediate_facts.copy()
    
    @property
    def reasoning(self) -> str:
        """Get simple reasoning explanation."""
        if not self.reasoning_steps:
            return "No rules fired"
        return "\n".join(self.reasoning_steps) 