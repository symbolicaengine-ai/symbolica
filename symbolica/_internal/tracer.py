"""
Execution Tracing
================

Simple tracer for debugging rule execution.
"""

from typing import Dict, Any, List
from ..core import Rule, ExecutionContext, ExecutionResult, Tracer


class StandardTracer(Tracer):
    """
    Standard tracer for debugging rule execution.
    
    Captures:
    - Rule evaluations
    - Action executions
    - Timing information
    - Context changes
    """
    
    def __init__(self):
        self.trace_data: Dict[str, Any] = {}
        self.rule_evaluations: List[Dict[str, Any]] = []
        self.action_executions: List[Dict[str, Any]] = []
    
    def begin_execution(self, context: ExecutionContext) -> None:
        """Start tracing execution."""
        self.trace_data = {
            'context_id': context.context_id,
            'start_time': context.start_time_ns,
            'original_facts': dict(context.original_facts.data),
            'trace_level': context.trace_level.value
        }
        self.rule_evaluations = []
        self.action_executions = []
    
    def trace_rule_evaluation(self, rule: Rule, result: bool, 
                             context: ExecutionContext) -> None:
        """Trace rule evaluation."""
        self.rule_evaluations.append({
            'rule_id': rule.id.value,
            'condition': rule.condition.expression,
            'result': result,
            'priority': rule.priority.value,
            'timestamp': context.execution_time_ns
        })
    
    def trace_action_execution(self, rule: Rule, action: Any,
                              context: ExecutionContext) -> None:
        """Trace action execution."""
        self.action_executions.append({
            'rule_id': rule.id.value,
            'action_type': action.type if hasattr(action, 'type') else str(type(action)),
            'action_params': action.parameters if hasattr(action, 'parameters') else {},
            'timestamp': context.execution_time_ns
        })
    
    def end_execution(self, result: ExecutionResult, 
                     context: ExecutionContext) -> Dict[str, Any]:
        """End tracing and return trace data."""
        self.trace_data.update({
            'end_time': context.execution_time_ns,
            'total_duration_ns': result.execution_time_ns,
            'fired_rules': [r.value for r in result.fired_rules],
            'final_verdict': result.verdict,
            'rule_evaluations': self.rule_evaluations,
            'action_executions': self.action_executions,
            'context_changes': context.verdict
        })
        
        return self.trace_data


class NoOpTracer(Tracer):
    """No-op tracer that doesn't collect any trace data."""
    
    def begin_execution(self, context: ExecutionContext) -> None:
        pass
    
    def trace_rule_evaluation(self, rule: Rule, result: bool, 
                             context: ExecutionContext) -> None:
        pass
    
    def trace_action_execution(self, rule: Rule, action: Any,
                              context: ExecutionContext) -> None:
        pass
    
    def end_execution(self, result: ExecutionResult, 
                     context: ExecutionContext) -> Dict[str, Any]:
        return {} 