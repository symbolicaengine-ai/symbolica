"""
Advanced Tracing and Debugging System
====================================

Comprehensive tracing system with:
- Detailed execution traces showing why rules fired/didn't fire
- Field dependency tracking during execution
- Performance metrics per rule and overall execution
- Rule coverage analysis and testing insights
- "Why did/didn't this rule fire?" explanations
- Trace visualization and export capabilities
"""

import time
import json
import threading
from typing import Dict, Any, List, Set, Optional, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import uuid

from ..core import Rule, RuleSet, Facts, ExecutionResult


class TraceLevel(Enum):
    """Trace detail levels."""
    NONE = "none"
    BASIC = "basic"
    DETAILED = "detailed"
    DEBUG = "debug"


class ExecutionPhase(Enum):
    """Execution phases for tracing."""
    START = "start"
    RULE_EVALUATION = "rule_evaluation"
    CONDITION_CHECK = "condition_check"
    ACTION_EXECUTION = "action_execution"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    OPTIMIZATION = "optimization"
    COMPLETION = "completion"


@dataclass
class FieldAccess:
    """Record of field access during execution."""
    field_name: str
    access_type: str  # 'read', 'write', 'check'
    value: Any
    timestamp: float
    rule_id: Optional[str] = None
    expression_context: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.perf_counter()


@dataclass
class ExpressionTrace:
    """Detailed trace of expression evaluation."""
    expression: str
    result: Any
    evaluation_time_ms: float
    field_accesses: List[FieldAccess]
    sub_expressions: List['ExpressionTrace']
    error: Optional[str] = None
    steps: List[str] = field(default_factory=list)
    
    def add_step(self, step: str) -> None:
        """Add an evaluation step."""
        self.steps.append(step)
    
    def explain_result(self) -> str:
        """Generate human-readable explanation of the result."""
        if self.error:
            return f"Expression failed: {self.error}"
        
        if not self.field_accesses:
            return f"Expression '{self.expression}' evaluated to {self.result} (no field dependencies)"
        
        field_values = {fa.field_name: fa.value for fa in self.field_accesses}
        return f"Expression '{self.expression}' evaluated to {self.result} with fields: {field_values}"


@dataclass
class RuleTrace:
    """Comprehensive trace of rule execution."""
    rule_id: str
    rule_priority: int
    phase: ExecutionPhase
    start_time: float
    end_time: float
    fired: bool
    condition_result: Optional[bool] = None
    condition_trace: Optional[ExpressionTrace] = None
    actions_executed: List[str] = field(default_factory=list)
    field_writes: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    skip_reason: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    
    @property
    def execution_time_ms(self) -> float:
        """Calculate execution time in milliseconds."""
        return (self.end_time - self.start_time) * 1000
    
    def explain_outcome(self) -> str:
        """Generate human-readable explanation of why rule fired or didn't."""
        if self.error:
            return f"Rule '{self.rule_id}' failed: {self.error}"
        
        if self.skip_reason:
            return f"Rule '{self.rule_id}' was skipped: {self.skip_reason}"
        
        if self.fired:
            explanation = f"Rule '{self.rule_id}' fired because its condition was true"
            if self.condition_trace:
                explanation += f": {self.condition_trace.explain_result()}"
            if self.actions_executed:
                explanation += f". Actions executed: {', '.join(self.actions_executed)}"
            return explanation
        else:
            explanation = f"Rule '{self.rule_id}' did not fire because its condition was false"
            if self.condition_trace:
                explanation += f": {self.condition_trace.explain_result()}"
            return explanation


@dataclass
class ExecutionTrace:
    """Complete trace of rule set execution."""
    trace_id: str
    start_time: float
    end_time: float
    facts_snapshot: Dict[str, Any]
    rule_traces: List[RuleTrace]
    execution_strategy: str
    total_rules_evaluated: int
    total_rules_fired: int
    total_field_accesses: int
    total_field_writes: int
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.trace_id:
            self.trace_id = str(uuid.uuid4())
    
    @property
    def total_execution_time_ms(self) -> float:
        """Total execution time in milliseconds."""
        return (self.end_time - self.start_time) * 1000
    
    @property
    def success_rate(self) -> float:
        """Percentage of rules that fired."""
        if self.total_rules_evaluated == 0:
            return 0.0
        return (self.total_rules_fired / self.total_rules_evaluated) * 100
    
    def get_rule_trace(self, rule_id: str) -> Optional[RuleTrace]:
        """Get trace for specific rule."""
        for trace in self.rule_traces:
            if trace.rule_id == rule_id:
                return trace
        return None
    
    def get_fired_rules(self) -> List[RuleTrace]:
        """Get traces of rules that fired."""
        return [trace for trace in self.rule_traces if trace.fired]
    
    def get_failed_rules(self) -> List[RuleTrace]:
        """Get traces of rules that failed."""
        return [trace for trace in self.rule_traces if trace.error]
    
    def get_skipped_rules(self) -> List[RuleTrace]:
        """Get traces of rules that were skipped."""
        return [trace for trace in self.rule_traces if trace.skip_reason]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        rule_times = [trace.execution_time_ms for trace in self.rule_traces]
        
        return {
            'total_execution_time_ms': self.total_execution_time_ms,
            'rules_evaluated': self.total_rules_evaluated,
            'rules_fired': self.total_rules_fired,
            'success_rate': self.success_rate,
            'avg_rule_time_ms': sum(rule_times) / len(rule_times) if rule_times else 0,
            'slowest_rule_time_ms': max(rule_times) if rule_times else 0,
            'fastest_rule_time_ms': min(rule_times) if rule_times else 0,
            'field_accesses': self.total_field_accesses,
            'field_writes': self.total_field_writes,
            'execution_strategy': self.execution_strategy
        }
    
    def explain_execution(self, rule_id: Optional[str] = None) -> str:
        """Generate human-readable explanation of execution."""
        if rule_id:
            trace = self.get_rule_trace(rule_id)
            return trace.explain_outcome() if trace else f"Rule '{rule_id}' not found in trace"
        
        # Overall execution summary
        fired_rules = self.get_fired_rules()
        failed_rules = self.get_failed_rules()
        
        summary = [
            f"Execution completed in {self.total_execution_time_ms:.2f}ms",
            f"Evaluated {self.total_rules_evaluated} rules, {self.total_rules_fired} fired",
            f"Success rate: {self.success_rate:.1f}%"
        ]
        
        if fired_rules:
            summary.append(f"Fired rules: {', '.join(t.rule_id for t in fired_rules)}")
        
        if failed_rules:
            summary.append(f"Failed rules: {', '.join(t.rule_id for t in failed_rules)}")
        
        return ". ".join(summary)


class ExecutionTracer:
    """
    Advanced execution tracer with comprehensive analysis capabilities.
    
    Features:
    - Multi-level tracing (none, basic, detailed, debug)
    - Real-time trace collection during execution
    - Field dependency tracking
    - Performance analysis
    - Rule coverage analysis
    - Export capabilities
    """
    
    def __init__(self, level: TraceLevel = TraceLevel.BASIC):
        self.level = level
        self.current_trace: Optional[ExecutionTrace] = None
        self.current_rule_trace: Optional[RuleTrace] = None
        self._traces: List[ExecutionTrace] = []
        self._trace_lock = threading.RLock()
        self._field_access_counts: Dict[str, int] = {}
        self._rule_coverage: Dict[str, int] = {}
        self._callbacks: List[Callable] = []
    
    def start_execution(self, facts: Facts, rule_set: RuleSet, 
                       strategy: str = "linear") -> str:
        """Start tracing a new execution."""
        if self.level == TraceLevel.NONE:
            return ""
        
        with self._trace_lock:
            trace_id = str(uuid.uuid4())
            
            self.current_trace = ExecutionTrace(
                trace_id=trace_id,
                start_time=time.perf_counter(),
                end_time=0,
                facts_snapshot=dict(facts.data) if facts else {},
                rule_traces=[],
                execution_strategy=strategy,
                total_rules_evaluated=0,
                total_rules_fired=0,
                total_field_accesses=0,
                total_field_writes=0
            )
            
            return trace_id
    
    def end_execution(self, result: ExecutionResult) -> Optional[ExecutionTrace]:
        """End current execution tracing."""
        if self.level == TraceLevel.NONE or not self.current_trace:
            return None
        
        with self._trace_lock:
            self.current_trace.end_time = time.perf_counter()
            self.current_trace.total_rules_evaluated = len(self.current_trace.rule_traces)
            self.current_trace.total_rules_fired = len(self.current_trace.get_fired_rules())
            
            # Calculate totals
            self.current_trace.total_field_accesses = sum(
                len(trace.condition_trace.field_accesses) 
                for trace in self.current_trace.rule_traces 
                if trace.condition_trace
            )
            self.current_trace.total_field_writes = sum(
                len(trace.field_writes) 
                for trace in self.current_trace.rule_traces
            )
            
            # Add performance metrics
            self.current_trace.performance_metrics = {
                'verdict': result.verdict,
                'execution_time_ms': result.execution_time_ms,
                'rules_fired': len(result.fired_rules),
                'field_changes': len(result.field_changes)
            }
            
            # Store completed trace
            completed_trace = self.current_trace
            self._traces.append(completed_trace)
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(completed_trace)
                except Exception:
                    pass  # Don't let callback errors break tracing
            
            # Clear current trace
            self.current_trace = None
            
            return completed_trace
    
    def start_rule_evaluation(self, rule: Rule) -> None:
        """Start tracing rule evaluation."""
        if self.level == TraceLevel.NONE or not self.current_trace:
            return
        
        with self._trace_lock:
            self.current_rule_trace = RuleTrace(
                rule_id=rule.id.value,
                rule_priority=rule.priority.value,
                phase=ExecutionPhase.RULE_EVALUATION,
                start_time=time.perf_counter(),
                end_time=0,
                fired=False
            )
            
            # Update coverage
            self._rule_coverage[rule.id.value] = self._rule_coverage.get(rule.id.value, 0) + 1
    
    def end_rule_evaluation(self, rule: Rule, fired: bool, error: Optional[str] = None) -> None:
        """End rule evaluation tracing."""
        if self.level == TraceLevel.NONE or not self.current_rule_trace:
            return
        
        with self._trace_lock:
            self.current_rule_trace.end_time = time.perf_counter()
            self.current_rule_trace.fired = fired
            self.current_rule_trace.error = error
            
            # Add to current trace
            if self.current_trace:
                self.current_trace.rule_traces.append(self.current_rule_trace)
            
            self.current_rule_trace = None
    
    def trace_condition_evaluation(self, expression: str, result: Any,
                                 field_accesses: List[FieldAccess],
                                 evaluation_time_ms: float,
                                 error: Optional[str] = None) -> None:
        """Trace condition evaluation."""
        if self.level == TraceLevel.NONE or not self.current_rule_trace:
            return
        
        with self._trace_lock:
            self.current_rule_trace.condition_result = bool(result) if error is None else None
            self.current_rule_trace.condition_trace = ExpressionTrace(
                expression=expression,
                result=result,
                evaluation_time_ms=evaluation_time_ms,
                field_accesses=field_accesses,
                sub_expressions=[],
                error=error
            )
            
            # Update field access counts
            for access in field_accesses:
                self._field_access_counts[access.field_name] = \
                    self._field_access_counts.get(access.field_name, 0) + 1
    
    def trace_action_execution(self, action_type: str, parameters: Dict[str, Any],
                             field_writes: Dict[str, Any]) -> None:
        """Trace action execution."""
        if self.level == TraceLevel.NONE or not self.current_rule_trace:
            return
        
        with self._trace_lock:
            self.current_rule_trace.actions_executed.append(action_type)
            self.current_rule_trace.field_writes.update(field_writes)
    
    def trace_rule_skip(self, rule: Rule, reason: str) -> None:
        """Trace rule being skipped."""
        if self.level == TraceLevel.NONE or not self.current_trace:
            return
        
        with self._trace_lock:
            skip_trace = RuleTrace(
                rule_id=rule.id.value,
                rule_priority=rule.priority.value,
                phase=ExecutionPhase.RULE_EVALUATION,
                start_time=time.perf_counter(),
                end_time=time.perf_counter(),
                fired=False,
                skip_reason=reason
            )
            
            self.current_trace.rule_traces.append(skip_trace)
    
    def trace_dependency_analysis(self, dependencies: Dict[str, List[str]]) -> None:
        """Trace dependency analysis results."""
        if self.level == TraceLevel.NONE or not self.current_trace:
            return
        
        with self._trace_lock:
            self.current_trace.metadata['dependencies'] = dependencies
    
    def add_step_trace(self, step: str) -> None:
        """Add a step trace to current rule's condition."""
        if (self.level in [TraceLevel.DETAILED, TraceLevel.DEBUG] and 
            self.current_rule_trace and 
            self.current_rule_trace.condition_trace):
            
            self.current_rule_trace.condition_trace.add_step(step)
    
    def get_trace_history(self, limit: Optional[int] = None) -> List[ExecutionTrace]:
        """Get trace history."""
        with self._trace_lock:
            if limit:
                return self._traces[-limit:]
            return self._traces.copy()
    
    def get_rule_coverage(self) -> Dict[str, int]:
        """Get rule coverage statistics."""
        with self._trace_lock:
            return self._rule_coverage.copy()
    
    def get_field_access_stats(self) -> Dict[str, int]:
        """Get field access statistics."""
        with self._trace_lock:
            return self._field_access_counts.copy()
    
    def analyze_performance(self, rule_id: Optional[str] = None) -> Dict[str, Any]:
        """Analyze performance across traces."""
        with self._trace_lock:
            if not self._traces:
                return {}
            
            if rule_id:
                # Analyze specific rule
                rule_traces = []
                for trace in self._traces:
                    rule_trace = trace.get_rule_trace(rule_id)
                    if rule_trace:
                        rule_traces.append(rule_trace)
                
                if not rule_traces:
                    return {}
                
                times = [t.execution_time_ms for t in rule_traces]
                fired_count = sum(1 for t in rule_traces if t.fired)
                
                return {
                    'rule_id': rule_id,
                    'executions': len(rule_traces),
                    'fired_count': fired_count,
                    'fire_rate': fired_count / len(rule_traces) if rule_traces else 0,
                    'avg_time_ms': sum(times) / len(times) if times else 0,
                    'min_time_ms': min(times) if times else 0,
                    'max_time_ms': max(times) if times else 0,
                    'total_time_ms': sum(times)
                }
            else:
                # Analyze overall performance
                total_times = [t.total_execution_time_ms for t in self._traces]
                success_rates = [t.success_rate for t in self._traces]
                
                return {
                    'total_executions': len(self._traces),
                    'avg_execution_time_ms': sum(total_times) / len(total_times) if total_times else 0,
                    'min_execution_time_ms': min(total_times) if total_times else 0,
                    'max_execution_time_ms': max(total_times) if total_times else 0,
                    'avg_success_rate': sum(success_rates) / len(success_rates) if success_rates else 0,
                    'rule_coverage': self.get_rule_coverage(),
                    'field_access_stats': self.get_field_access_stats()
                }
    
    def explain_execution(self, trace_id: Optional[str] = None, 
                         rule_id: Optional[str] = None) -> str:
        """Explain execution results."""
        with self._trace_lock:
            if trace_id:
                trace = next((t for t in self._traces if t.trace_id == trace_id), None)
                if not trace:
                    return f"Trace {trace_id} not found"
                return trace.explain_execution(rule_id)
            
            elif self.current_trace:
                return self.current_trace.explain_execution(rule_id)
            
            elif self._traces:
                return self._traces[-1].explain_execution(rule_id)
            
            else:
                return "No execution traces available"
    
    def export_traces(self, output_path: Path, format: str = "json") -> None:
        """Export traces to file."""
        with self._trace_lock:
            if format == "json":
                data = {
                    'traces': [self._trace_to_dict(trace) for trace in self._traces],
                    'summary': {
                        'total_traces': len(self._traces),
                        'rule_coverage': self.get_rule_coverage(),
                        'field_access_stats': self.get_field_access_stats()
                    }
                }
                
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
    
    def _trace_to_dict(self, trace: ExecutionTrace) -> Dict[str, Any]:
        """Convert trace to dictionary for serialization."""
        return {
            'trace_id': trace.trace_id,
            'start_time': trace.start_time,
            'end_time': trace.end_time,
            'total_execution_time_ms': trace.total_execution_time_ms,
            'facts_snapshot': trace.facts_snapshot,
            'execution_strategy': trace.execution_strategy,
            'performance_summary': trace.get_performance_summary(),
            'rule_traces': [
                {
                    'rule_id': rt.rule_id,
                    'rule_priority': rt.rule_priority,
                    'fired': rt.fired,
                    'execution_time_ms': rt.execution_time_ms,
                    'condition_result': rt.condition_result,
                    'actions_executed': rt.actions_executed,
                    'field_writes': rt.field_writes,
                    'error': rt.error,
                    'skip_reason': rt.skip_reason,
                    'explanation': rt.explain_outcome()
                }
                for rt in trace.rule_traces
            ]
        }
    
    def add_callback(self, callback: Callable[[ExecutionTrace], None]) -> None:
        """Add callback for trace completion."""
        self._callbacks.append(callback)
    
    def clear_history(self) -> None:
        """Clear trace history."""
        with self._trace_lock:
            self._traces.clear()
            self._field_access_counts.clear()
            self._rule_coverage.clear()
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information."""
        with self._trace_lock:
            return {
                'trace_level': self.level.value,
                'current_trace_active': self.current_trace is not None,
                'current_rule_active': self.current_rule_trace is not None,
                'total_traces': len(self._traces),
                'callbacks_registered': len(self._callbacks)
            }


class TraceAnalyzer:
    """
    Advanced trace analyzer for insights and debugging.
    
    Features:
    - Rule performance analysis
    - Field usage patterns
    - Execution bottleneck identification
    - Rule coverage analysis
    - Debugging recommendations
    """
    
    def __init__(self, traces: List[ExecutionTrace]):
        self.traces = traces
    
    def analyze_rule_performance(self, rule_id: str) -> Dict[str, Any]:
        """Analyze performance of a specific rule."""
        rule_data = []
        
        for trace in self.traces:
            rule_trace = trace.get_rule_trace(rule_id)
            if rule_trace:
                rule_data.append({
                    'execution_time_ms': rule_trace.execution_time_ms,
                    'fired': rule_trace.fired,
                    'error': rule_trace.error,
                    'trace_id': trace.trace_id
                })
        
        if not rule_data:
            return {'error': f'No data found for rule {rule_id}'}
        
        times = [d['execution_time_ms'] for d in rule_data]
        fired_count = sum(1 for d in rule_data if d['fired'])
        error_count = sum(1 for d in rule_data if d['error'])
        
        return {
            'rule_id': rule_id,
            'total_executions': len(rule_data),
            'fired_count': fired_count,
            'fire_rate': fired_count / len(rule_data),
            'error_count': error_count,
            'error_rate': error_count / len(rule_data),
            'avg_execution_time_ms': sum(times) / len(times),
            'min_execution_time_ms': min(times),
            'max_execution_time_ms': max(times),
            'performance_classification': self._classify_performance(sum(times) / len(times))
        }
    
    def find_bottlenecks(self, threshold_ms: float = 10.0) -> List[Dict[str, Any]]:
        """Find performance bottlenecks."""
        bottlenecks = []
        
        # Analyze rule performance
        rule_times = {}
        for trace in self.traces:
            for rule_trace in trace.rule_traces:
                if rule_trace.rule_id not in rule_times:
                    rule_times[rule_trace.rule_id] = []
                rule_times[rule_trace.rule_id].append(rule_trace.execution_time_ms)
        
        for rule_id, times in rule_times.items():
            avg_time = sum(times) / len(times)
            if avg_time > threshold_ms:
                bottlenecks.append({
                    'type': 'slow_rule',
                    'rule_id': rule_id,
                    'avg_time_ms': avg_time,
                    'executions': len(times),
                    'recommendation': f'Rule {rule_id} takes {avg_time:.2f}ms on average - consider optimizing'
                })
        
        return sorted(bottlenecks, key=lambda x: x['avg_time_ms'], reverse=True)
    
    def analyze_field_usage(self) -> Dict[str, Any]:
        """Analyze field usage patterns."""
        field_reads = {}
        field_writes = {}
        
        for trace in self.traces:
            for rule_trace in trace.rule_traces:
                if rule_trace.condition_trace:
                    for access in rule_trace.condition_trace.field_accesses:
                        if access.field_name not in field_reads:
                            field_reads[access.field_name] = 0
                        field_reads[access.field_name] += 1
                
                for field_name in rule_trace.field_writes:
                    if field_name not in field_writes:
                        field_writes[field_name] = 0
                    field_writes[field_name] += 1
        
        return {
            'most_read_fields': sorted(field_reads.items(), key=lambda x: x[1], reverse=True)[:10],
            'most_written_fields': sorted(field_writes.items(), key=lambda x: x[1], reverse=True)[:10],
            'unused_fields': self._find_unused_fields(field_reads, field_writes),
            'read_write_ratio': self._calculate_read_write_ratio(field_reads, field_writes)
        }
    
    def get_debugging_recommendations(self) -> List[str]:
        """Get debugging recommendations based on trace analysis."""
        recommendations = []
        
        # Check for rules that never fire
        rule_fire_rates = {}
        for trace in self.traces:
            for rule_trace in trace.rule_traces:
                if rule_trace.rule_id not in rule_fire_rates:
                    rule_fire_rates[rule_trace.rule_id] = {'fired': 0, 'total': 0}
                rule_fire_rates[rule_trace.rule_id]['total'] += 1
                if rule_trace.fired:
                    rule_fire_rates[rule_trace.rule_id]['fired'] += 1
        
        for rule_id, stats in rule_fire_rates.items():
            fire_rate = stats['fired'] / stats['total']
            if fire_rate == 0 and stats['total'] > 1:
                recommendations.append(f"Rule '{rule_id}' never fires - check its condition")
            elif fire_rate < 0.1 and stats['total'] > 10:
                recommendations.append(f"Rule '{rule_id}' rarely fires ({fire_rate:.1%}) - consider if it's necessary")
        
        # Check for performance issues
        bottlenecks = self.find_bottlenecks()
        if bottlenecks:
            recommendations.append(f"Found {len(bottlenecks)} slow rules - consider optimization")
        
        return recommendations
    
    def _classify_performance(self, avg_time_ms: float) -> str:
        """Classify rule performance."""
        if avg_time_ms < 1.0:
            return "excellent"
        elif avg_time_ms < 5.0:
            return "good"
        elif avg_time_ms < 10.0:
            return "acceptable"
        else:
            return "needs_optimization"
    
    def _find_unused_fields(self, field_reads: Dict[str, int], 
                          field_writes: Dict[str, int]) -> List[str]:
        """Find fields that are never used."""
        # This would need access to the original facts to be complete
        # For now, return fields that are written but never read
        written_fields = set(field_writes.keys())
        read_fields = set(field_reads.keys())
        
        return list(written_fields - read_fields)
    
    def _calculate_read_write_ratio(self, field_reads: Dict[str, int], 
                                  field_writes: Dict[str, int]) -> float:
        """Calculate overall read/write ratio."""
        total_reads = sum(field_reads.values())
        total_writes = sum(field_writes.values())
        
        if total_writes == 0:
            return float('inf')
        
        return total_reads / total_writes


# Convenience functions
def create_tracer(level: TraceLevel = TraceLevel.BASIC) -> ExecutionTracer:
    """Create execution tracer."""
    return ExecutionTracer(level)


def analyze_traces(traces: List[ExecutionTrace]) -> TraceAnalyzer:
    """Create trace analyzer."""
    return TraceAnalyzer(traces) 