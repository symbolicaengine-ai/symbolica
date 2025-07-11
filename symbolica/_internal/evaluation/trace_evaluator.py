"""
Trace Evaluator
===============

Wrapper around CoreEvaluator that adds simple tracing.
Extracted from evaluator.py to follow Single Responsibility Principle.
"""

import ast
from dataclasses import dataclass
from typing import Any, Dict, TYPE_CHECKING
from .core_evaluator import CoreEvaluator
from ...core.exceptions import EvaluationError, FunctionError, ValidationError

if TYPE_CHECKING:
    from ...core.models import ExecutionContext


@dataclass
class ConditionTrace:
    """Simple trace information for condition evaluation."""
    expression: str
    result: bool
    field_values: Dict[str, Any]
    
    def explain(self) -> str:
        """Generate human-readable explanation of evaluation."""
        if self.field_values:
            field_items = [f"{k}={v}" for k, v in self.field_values.items()]
            return f"condition '{self.expression}' evaluated to {self.result} with {', '.join(field_items)}"
        else:
            return f"condition '{self.expression}' evaluated to {self.result}"


class TraceEvaluator:
    """Evaluator that wraps CoreEvaluator and adds simple tracing."""
    
    def __init__(self):
        """Initialize trace evaluator with core evaluator."""
        self._core = CoreEvaluator()
    
    def register_function(self, name: str, func: Any) -> None:
        """Register a custom function."""
        self._core.register_function(name, func)
    
    def unregister_function(self, name: str) -> None:
        """Remove a custom function."""
        self._core.unregister_function(name)
    
    def evaluate_with_trace(self, condition_expr: str, context: 'ExecutionContext') -> ConditionTrace:
        """Evaluate condition and return trace information."""
        try:
            result, field_values = self._core.evaluate(condition_expr, context)
            return ConditionTrace(condition_expr, bool(result), field_values)
        except (EvaluationError, FunctionError, ValidationError):
            # Re-raise our custom exceptions with additional context
            raise
        except SyntaxError as e:
            raise EvaluationError(
                f"Invalid syntax in condition", 
                expression=condition_expr,
                field_values={'syntax_error': str(e)}
            )
        except Exception as e:
            raise EvaluationError(
                f"Unexpected evaluation error: {str(e)}", 
                expression=condition_expr
            ) 