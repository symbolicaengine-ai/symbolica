"""
Built-in Functions for Rule Evaluation
======================================

Safe implementations of built-in functions used in rule conditions.
Extracted from evaluator.py to follow Single Responsibility Principle.
"""

from typing import Any, List, Dict, Callable
from ...core.infrastructure.exceptions import EvaluationError


def safe_len(args: List[Any]) -> int:
    """Safe implementation of len() function."""
    if not args:
        raise EvaluationError("len() requires exactly 1 argument")
    if len(args) != 1:
        raise EvaluationError(f"len() takes exactly 1 argument ({len(args)} given)")
    
    obj = args[0]
    if obj is None:
        return 0
    
    try:
        return len(obj)
    except TypeError:
        raise EvaluationError(f"len() argument must be a sequence, not {type(obj).__name__}")


def safe_sum(args: List[Any]) -> float:
    """Safe implementation of sum() function."""
    if not args:
        raise EvaluationError("sum() requires exactly 1 argument")
    if len(args) != 1:
        raise EvaluationError(f"sum() takes exactly 1 argument ({len(args)} given)")
    
    obj = args[0]
    if obj is None:
        return 0
    
    try:
        return sum(obj)
    except TypeError:
        raise EvaluationError(f"sum() argument must be iterable of numbers, not {type(obj).__name__}")


def safe_contains(args: List[Any]) -> bool:
    """Safe implementation of contains() function."""
    if len(args) != 2:
        raise EvaluationError(f"contains() takes exactly 2 arguments ({len(args)} given)")
    
    container, item = args
    if container is None:
        return False
    
    try:
        return item in container
    except TypeError:
        raise EvaluationError(f"contains() first argument must be a container, not {type(container).__name__}")


def safe_abs(args: List[Any]) -> float:
    """Safe implementation of abs() function."""
    if not args:
        raise EvaluationError("abs() requires exactly 1 argument")
    if len(args) != 1:
        raise EvaluationError(f"abs() takes exactly 1 argument ({len(args)} given)")
    
    obj = args[0]
    if obj is None:
        raise EvaluationError("abs() argument cannot be None")
    
    try:
        return abs(obj)
    except TypeError:
        raise EvaluationError(f"abs() argument must be a number, not {type(obj).__name__}")


def safe_startswith(args: List[Any]) -> bool:
    """Safe implementation of startswith() function."""
    if len(args) != 2:
        return False
    if not isinstance(args[0], str):
        return False
    return args[0].startswith(args[1])


def safe_endswith(args: List[Any]) -> bool:
    """Safe implementation of endswith() function."""
    if len(args) != 2:
        return False
    if not isinstance(args[0], str):
        return False
    return args[0].endswith(args[1])


# Built-in function registry
BUILTIN_FUNCTIONS: Dict[str, Callable] = {
    'len': safe_len,
    'sum': safe_sum,
    'startswith': safe_startswith,
    'endswith': safe_endswith,
    'contains': safe_contains,
    'abs': safe_abs
}

# Function descriptions for documentation
BUILTIN_FUNCTION_DESCRIPTIONS: Dict[str, str] = {
    'len': 'Get length of sequence',
    'sum': 'Sum elements of sequence', 
    'abs': 'Absolute value',
    'startswith': 'Check if string starts with substring',
    'endswith': 'Check if string ends with substring',
    'contains': 'Check if sequence contains element'
}


def get_builtin_functions() -> Dict[str, Callable]:
    """Get all built-in functions."""
    return BUILTIN_FUNCTIONS.copy()


def get_builtin_function_descriptions() -> Dict[str, str]:
    """Get descriptions of all built-in functions."""
    return BUILTIN_FUNCTION_DESCRIPTIONS.copy() 