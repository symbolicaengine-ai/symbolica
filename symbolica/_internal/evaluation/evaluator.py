"""
AST Expression Evaluator
========================

Orchestrates focused evaluator components for safe, sandboxed expression evaluation.
Refactored from God object to follow Single Responsibility Principle.
"""

from typing import Any, Dict, Set, Callable, TYPE_CHECKING, Optional
from ...core.interfaces import ConditionEvaluator
from .core_evaluator import CoreEvaluator
from .trace_evaluator import TraceEvaluator, ConditionTrace
from .execution_path_evaluator import ExecutionPathEvaluator
from .field_extractor import FieldExtractor
from .builtin_functions import get_builtin_function_descriptions

if TYPE_CHECKING:
    from ...core.models import ExecutionContext
    from .execution_path import ExecutionPath
    from ...llm.prompt_evaluator import PromptEvaluator


class ASTEvaluator(ConditionEvaluator):
    """Orchestrating evaluator that delegates to focused components.
    
    This class maintains the same interface as the original God object
    but delegates responsibilities to specialized components:
    - CoreEvaluator: Basic AST evaluation
    - TraceEvaluator: Simple tracing
    - ExecutionPathEvaluator: Detailed execution paths
    - FieldExtractor: Field name extraction
    """
    
    def __init__(self, prompt_evaluator: Optional['PromptEvaluator'] = None):
        """Initialize evaluator with focused components."""
        # Core components (pass prompt evaluator to all)
        self._core = CoreEvaluator(prompt_evaluator)
        self._trace_evaluator = TraceEvaluator(prompt_evaluator)
        self._execution_path_evaluator = ExecutionPathEvaluator(prompt_evaluator)
        self._field_extractor = FieldExtractor()
        
        # Keep function registry synchronized across components
        self._update_function_registry()
    
    def _update_function_registry(self) -> None:
        """Update field extractor with current function names."""
        all_functions = set(self._core._builtin_functions.keys()) | set(self._core._custom_functions.keys())
        self._field_extractor.update_function_names(all_functions)
    
    def register_function(self, name: str, func: Callable) -> None:
        """Register a custom function across all components."""
        # Validate function registration
        if not callable(func):
            from ...core.exceptions import FunctionError
            raise FunctionError(f"Function must be callable", function_name=name)
        
        # Use centralized validation from IdentifierValidator
        from ...core.validation.identifier_validator import IdentifierValidator
        identifier_validator = IdentifierValidator()
        identifier_validator.validate_identifier(name, f"Function name '{name}'")
        
        # Register with all components
        self._core.register_function(name, func)
        self._trace_evaluator.register_function(name, func)
        self._execution_path_evaluator.register_function(name, func)
        
        # Update field extractor
        self._update_function_registry()
    
    def unregister_function(self, name: str) -> None:
        """Remove a custom function from all components."""
        self._core.unregister_function(name)
        self._trace_evaluator.unregister_function(name)
        self._execution_path_evaluator.unregister_function(name)
        
        # Update field extractor
        self._update_function_registry()
    
    def list_functions(self) -> Dict[str, str]:
        """List all available functions."""
        builtin_descriptions = get_builtin_function_descriptions()
        custom_descriptions = {
            name: f'Custom function: {func.__name__ if hasattr(func, "__name__") else "lambda"}' 
            for name, func in self._core._custom_functions.items()
        }
        return {**builtin_descriptions, **custom_descriptions}
    
    # Core evaluation methods (delegate to components)
    def evaluate(self, condition_expr: str, context: 'ExecutionContext') -> bool:
        """Evaluate condition expression."""
        result, _ = self._core.evaluate(condition_expr, context)
        return bool(result)
    
    def evaluate_with_trace(self, condition_expr: str, context: 'ExecutionContext') -> ConditionTrace:
        """Evaluate condition and return trace information."""
        return self._trace_evaluator.evaluate_with_trace(condition_expr, context)
    
    def evaluate_with_execution_path(self, condition_expr: str, context: 'ExecutionContext') -> 'ExecutionPath':
        """Evaluate condition and return detailed execution path."""
        return self._execution_path_evaluator.evaluate_with_execution_path(condition_expr, context)
    
    def extract_fields(self, condition_expr: str) -> Set[str]:
        """Extract field names from condition expression."""
        return self._field_extractor.extract_fields_from_condition(condition_expr)


 