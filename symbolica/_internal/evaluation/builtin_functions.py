"""
Built-in Functions
==================

Safe implementations of built-in functions for expression evaluation.
Extracted from evaluator.py to centralize function definitions.
"""

from typing import Dict, Callable, Any, List, Optional, TYPE_CHECKING
from ...core.exceptions import EvaluationError

if TYPE_CHECKING:
    from ...llm.prompt_evaluator import PromptEvaluator


def get_builtin_functions(prompt_evaluator: Optional['PromptEvaluator'] = None) -> Dict[str, Callable]:
    """Get dictionary of all built-in functions."""
    functions = {
        'len': safe_len,
        'sum': safe_sum,
        'abs': safe_abs,
        'max': safe_max,
        'min': safe_min,
        'startswith': safe_startswith,
        'endswith': safe_endswith,
        'contains': safe_contains
    }
    
    # Add PROMPT() function if evaluator provided
    # Note: PROMPT() is handled specially in CoreEvaluator._eval_call()
    # We add a placeholder here so it appears in function lists
    if prompt_evaluator:
        def prompt_placeholder(args):
            raise EvaluationError("PROMPT() function should be handled by CoreEvaluator")
        functions['PROMPT'] = prompt_placeholder
    
    return functions


def get_builtin_function_descriptions(include_llm: bool = False) -> Dict[str, str]:
    """Get descriptions of all built-in functions."""
    descriptions = {
        'len': 'Get length of sequence',
        'sum': 'Sum elements of sequence',
        'abs': 'Absolute value',
        'max': 'Maximum value from sequence',
        'min': 'Minimum value from sequence',
        'startswith': 'Check if string starts with substring',
        'endswith': 'Check if string ends with substring',
        'contains': 'Check if sequence contains element'
    }
    
    # Add LLM function descriptions if requested
    if include_llm:
        descriptions['PROMPT'] = 'Execute LLM prompt with variable substitution and type conversion'
    
    return descriptions


# Built-in function implementations
def safe_len(args: List[Any]) -> int:
    """Safe implementation of len() function."""
    if len(args) != 1:
        raise EvaluationError("len() takes exactly one argument")
    
    obj = args[0]
    if obj is None:
        return 0
    
    try:
        return len(obj)
    except TypeError:
        raise EvaluationError(f"object of type '{type(obj).__name__}' has no len()")


def safe_sum(args: List[Any]) -> float:
    """Safe implementation of sum() function."""
    if len(args) != 1:
        raise EvaluationError("sum() takes exactly one argument")
    
    iterable = args[0]
    if iterable is None:
        return 0
    
    try:
        return sum(iterable)
    except TypeError as e:
        raise EvaluationError(f"sum() error: {e}")


def safe_abs(args: List[Any]) -> float:
    """Safe implementation of abs() function."""
    if len(args) != 1:
        raise EvaluationError("abs() takes exactly one argument")
    
    value = args[0]
    if value is None:
        raise EvaluationError("abs() cannot operate on None")
    
    try:
        return abs(value)
    except TypeError:
        raise EvaluationError(f"bad operand type for abs(): '{type(value).__name__}'")


def safe_max(args: List[Any]) -> Any:
    """Safe implementation of max() function."""
    if len(args) != 1:
        raise EvaluationError("max() takes exactly one argument")
    
    iterable = args[0]
    if iterable is None:
        raise EvaluationError("max() cannot operate on None")
    
    try:
        if hasattr(iterable, '__iter__') and not isinstance(iterable, (str, bytes)):
            # Convert to list to handle generators and check if empty
            items = list(iterable)
            if not items:
                raise EvaluationError("max() arg is an empty sequence")
            return max(items)
        else:
            raise EvaluationError(f"'{type(iterable).__name__}' object is not iterable")
    except (TypeError, ValueError) as e:
        raise EvaluationError(f"max() error: {e}")


def safe_min(args: List[Any]) -> Any:
    """Safe implementation of min() function."""
    if len(args) != 1:
        raise EvaluationError("min() takes exactly one argument")
    
    iterable = args[0]
    if iterable is None:
        raise EvaluationError("min() cannot operate on None")
    
    try:
        if hasattr(iterable, '__iter__') and not isinstance(iterable, (str, bytes)):
            # Convert to list to handle generators and check if empty
            items = list(iterable)
            if not items:
                raise EvaluationError("min() arg is an empty sequence")
            return min(items)
        else:
            raise EvaluationError(f"'{type(iterable).__name__}' object is not iterable")
    except (TypeError, ValueError) as e:
        raise EvaluationError(f"min() error: {e}")


def safe_startswith(args: List[Any]) -> bool:
    """Safe implementation of startswith() function."""
    if len(args) != 2:
        raise EvaluationError("startswith() takes exactly two arguments")
    
    string, prefix = args
    if string is None or prefix is None:
        return False
    
    try:
        return str(string).startswith(str(prefix))
    except Exception as e:
        raise EvaluationError(f"startswith() error: {e}")


def safe_endswith(args: List[Any]) -> bool:
    """Safe implementation of endswith() function."""
    if len(args) != 2:
        raise EvaluationError("endswith() takes exactly two arguments")
    
    string, suffix = args
    if string is None or suffix is None:
        return False
    
    try:
        return str(string).endswith(str(suffix))
    except Exception as e:
        raise EvaluationError(f"endswith() error: {e}")


def safe_contains(args: List[Any]) -> bool:
    """Safe implementation of contains() function."""
    if len(args) != 2:
        raise EvaluationError("contains() takes exactly two arguments")
    
    container, item = args
    if container is None:
        return False
    
    try:
        return item in container
    except TypeError:
        # If container doesn't support 'in' operator
        return False 