"""
Simple Execution Path Tracking
==============================

Lightweight decision path tracking that annotates AST evaluation 
without duplicating the AST structure. Focuses on what actually matters:
which conditions were evaluated and what their results were.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from enum import Enum


class OperationType(Enum):
    """Types of operations we track."""
    COMPARISON = "comparison"
    BOOLEAN_AND = "and"
    BOOLEAN_OR = "or"
    BOOLEAN_NOT = "not"
    FUNCTION_CALL = "function"
    FIELD_ACCESS = "field"
    LITERAL = "literal"


@dataclass
class ExecutionStep:
    """A single step in the execution path."""
    step_id: int
    operation: OperationType
    expression: str
    result: Any
    details: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    children: List[int] = field(default_factory=list)  # References to child step IDs
    
    def explain(self) -> str:
        """Generate human-readable explanation of this step."""
        if self.operation == OperationType.COMPARISON:
            left = self.details.get('left_value')
            op = self.details.get('operator', '?')
            right = self.details.get('right_value')
            return f"{left} {op} {right} = {self.result}"
            
        elif self.operation == OperationType.BOOLEAN_AND:
            success_count = sum(1 for child_result in self.details.get('child_results', []) if child_result)
            total_count = len(self.details.get('child_results', []))
            if self.result:
                return f"All {total_count} conditions were true"
            else:
                return f"Failed: only {success_count}/{total_count} conditions were true"
                
        elif self.operation == OperationType.BOOLEAN_OR:
            if self.result:
                return f"Succeeded: at least one condition was true"
            else:
                return f"Failed: no conditions were true"
                
        elif self.operation == OperationType.BOOLEAN_NOT:
            operand = self.details.get('operand_value')
            return f"not {operand} = {self.result}"
            
        elif self.operation == OperationType.FUNCTION_CALL:
            func_name = self.details.get('function_name', 'unknown')
            args = self.details.get('arguments', [])
            error = self.details.get('error')
            if error:
                return f"{func_name}({args}) failed: {error}"
            else:
                return f"{func_name}({args}) = {self.result}"
                
        elif self.operation == OperationType.FIELD_ACCESS:
            field_name = self.details.get('field_name', 'unknown')
            is_missing = self.details.get('is_missing', False)
            if is_missing:
                return f"Field '{field_name}' not found, using {self.result}"
            else:
                return f"Field '{field_name}' = {self.result}"
                
        elif self.operation == OperationType.LITERAL:
            return f"Literal {self.result}"
            
        return f"{self.expression} = {self.result}"


@dataclass
class ExecutionPath:
    """Lightweight execution path for condition evaluation."""
    expression: str
    result: bool
    steps: List[ExecutionStep] = field(default_factory=list)
    total_time_ms: float = 0.0
    field_values: Dict[str, Any] = field(default_factory=dict)
    
    def add_step(self, operation: OperationType, expression: str, result: Any, 
                 details: Optional[Dict[str, Any]] = None, execution_time_ms: float = 0.0) -> int:
        """Add a step to the execution path and return its ID."""
        step_id = len(self.steps)
        step = ExecutionStep(
            step_id=step_id,
            operation=operation,
            expression=expression,
            result=result,
            details=details or {},
            execution_time_ms=execution_time_ms
        )
        self.steps.append(step)
        return step_id
    
    def add_child(self, parent_id: int, child_id: int) -> None:
        """Add a child relationship between steps."""
        if 0 <= parent_id < len(self.steps):
            self.steps[parent_id].children.append(child_id)
    
    def get_critical_path(self) -> List[ExecutionStep]:
        """Get the critical path that led to the final result."""
        if not self.steps:
            return []
        
        # For boolean operations, follow the path that determined the result
        critical_steps = []
        
        def trace_critical(step_id: int, depth: int = 0):
            if step_id >= len(self.steps):
                return
                
            step = self.steps[step_id]
            critical_steps.append(step)
            
            # For boolean operations, follow the critical child
            if step.operation == OperationType.BOOLEAN_AND and not step.result:
                # Find first false child
                child_results = step.details.get('child_results', [])
                for i, child_result in enumerate(child_results):
                    if not child_result and i < len(step.children):
                        trace_critical(step.children[i], depth + 1)
                        break
            elif step.operation == OperationType.BOOLEAN_OR and step.result:
                # Find first true child
                child_results = step.details.get('child_results', [])
                for i, child_result in enumerate(child_results):
                    if child_result and i < len(step.children):
                        trace_critical(step.children[i], depth + 1)
                        break
            elif step.children:
                # For other operations, follow first child
                trace_critical(step.children[0], depth + 1)
        
        # Start from root (last step is usually the root)
        if self.steps:
            trace_critical(len(self.steps) - 1)
        
        return critical_steps
    
    def explain(self) -> str:
        """Generate human-readable explanation of the execution."""
        if not self.steps:
            return f"Expression '{self.expression}' evaluated to {self.result}"
        
        # Get the critical path that led to the result
        critical_path = self.get_critical_path()
        
        if len(critical_path) == 1:
            return critical_path[0].explain()
        
        # Build explanation from critical path
        explanations = []
        for i, step in enumerate(critical_path):
            if i == 0:
                explanations.append(f"Expression '{self.expression}' = {self.result}")
            explanations.append(f"  → {step.explain()}")
        
        return "\n".join(explanations)
    
    def get_llm_context(self) -> Dict[str, Any]:
        """Get context optimized for LLM processing."""
        critical_path = self.get_critical_path()
        
        return {
            'expression': self.expression,
            'result': self.result,
            'total_time_ms': self.total_time_ms,
            'field_values': self.field_values,
            'explanation': self.explain(),
            'critical_path': [
                {
                    'operation': step.operation.value,
                    'explanation': step.explain(),
                    'result': step.result,
                    'time_ms': step.execution_time_ms
                }
                for step in critical_path
            ],
            'performance_stats': {
                'total_steps': len(self.steps),
                'total_time_ms': self.total_time_ms,
                'avg_step_time_ms': self.total_time_ms / len(self.steps) if self.steps else 0,
                'function_calls': len([s for s in self.steps if s.operation == OperationType.FUNCTION_CALL]),
                'field_accesses': len([s for s in self.steps if s.operation == OperationType.FIELD_ACCESS])
            }
        }
    
    def get_condition_breakdown(self) -> Dict[str, Any]:
        """Get detailed breakdown of conditions for debugging."""
        breakdown = {
            'comparisons': [],
            'function_calls': [],
            'field_accesses': [],
            'boolean_operations': []
        }
        
        for step in self.steps:
            step_info = {
                'expression': step.expression,
                'result': step.result,
                'explanation': step.explain(),
                'time_ms': step.execution_time_ms
            }
            
            if step.operation == OperationType.COMPARISON:
                breakdown['comparisons'].append(step_info)
            elif step.operation == OperationType.FUNCTION_CALL:
                breakdown['function_calls'].append(step_info)
            elif step.operation == OperationType.FIELD_ACCESS:
                breakdown['field_accesses'].append(step_info)
            elif step.operation in (OperationType.BOOLEAN_AND, OperationType.BOOLEAN_OR, OperationType.BOOLEAN_NOT):
                breakdown['boolean_operations'].append(step_info)
        
        return breakdown


class ExecutionPathBuilder:
    """Builder for creating execution paths during AST evaluation."""
    
    def __init__(self, expression: str):
        self.path = ExecutionPath(expression=expression, result=False)
        self.step_stack: List[int] = []  # Stack of parent step IDs
    
    def start_operation(self, operation: OperationType, expression: str) -> int:
        """Start a new operation and return its step ID."""
        # Create placeholder step
        step_id = self.path.add_step(operation, expression, None)
        
        # Link to parent if there is one
        if self.step_stack:
            parent_id = self.step_stack[-1]
            self.path.add_child(parent_id, step_id)
        
        self.step_stack.append(step_id)
        return step_id
    
    def finish_operation(self, step_id: int, result: Any, details: Optional[Dict[str, Any]] = None, execution_time_ms: float = 0.0):
        """Finish an operation with its result."""
        if step_id < len(self.path.steps):
            step = self.path.steps[step_id]
            step.result = result
            step.details.update(details or {})
            step.execution_time_ms = execution_time_ms
        
        # Pop from stack
        if self.step_stack and self.step_stack[-1] == step_id:
            self.step_stack.pop()
    
    def add_field_access(self, field_name: str, value: Any, is_missing: bool = False) -> None:
        """Record field access."""
        self.path.field_values[field_name] = value
        
        details = {
            'field_name': field_name,
            'field_value': value,
            'is_missing': is_missing
        }
        
        step_id = self.path.add_step(
            OperationType.FIELD_ACCESS,
            field_name,
            value,
            details
        )
        
        # Link to current parent
        if self.step_stack:
            parent_id = self.step_stack[-1]
            self.path.add_child(parent_id, step_id)
    
    def finalize(self, final_result: bool, total_time_ms: float) -> ExecutionPath:
        """Finalize the execution path."""
        self.path.result = final_result
        self.path.total_time_ms = total_time_ms
        return self.path 