"""
symbolica.compiler.ast
======================

Comprehensive Abstract Syntax Tree for Symbolica rule expressions.

Supports all expression categories:
- Boolean combinators (All, Any, Not)
- Comparison operators (==, !=, >, >=, <, <=, in, not in)
- Arithmetic operations (+, -, *, /, %, parentheses)
- String functions (startswith, endswith, contains)
- Null checks (== null, != null)

Each AST node implements:
    evaluate(facts: Dict[str, Any], cache: Dict[str, bool]) -> Any
"""

from __future__ import annotations

import operator
from typing import Any, Dict, List, Union


# ============================================================================
# OPERATORS AND HELPERS
# ============================================================================

# Comparison operators
_COMPARISON_OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
}

# Membership operators
_MEMBERSHIP_OPS = {
    "in": lambda x, y: x in y if y is not None else False,
    "not in": lambda x, y: x not in y if y is not None else True,
}

# Arithmetic operators
_ARITHMETIC_OPS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "%": operator.mod,
}

# String helper functions
def _startswith(text: Any, prefix: Any) -> bool:
    """Check if text starts with prefix."""
    if text is None or prefix is None:
        return False
    return str(text).startswith(str(prefix))

def _endswith(text: Any, suffix: Any) -> bool:
    """Check if text ends with suffix."""
    if text is None or suffix is None:
        return False
    return str(text).endswith(str(suffix))

def _contains(text: Any, substr: Any) -> bool:
    """Check if text contains substring."""
    if text is None or substr is None:
        return False
    return str(substr) in str(text)

_STRING_FUNCTIONS = {
    "startswith": _startswith,
    "endswith": _endswith,
    "contains": _contains,
}


# ============================================================================
# AST NODE BASE CLASS
# ============================================================================

class ASTNode:
    """Base class for all AST nodes."""
    
    __slots__ = ()
    
    def evaluate(self, facts: Dict[str, Any], cache: Dict[str, bool]) -> Any:
        """Evaluate this AST node against the given facts."""
        raise NotImplementedError
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


# ============================================================================
# LEAF NODES (VALUES AND REFERENCES)
# ============================================================================

class Literal(ASTNode):
    """Literal value node (numbers, strings, booleans, null, lists)."""
    
    __slots__ = ("value", "_cache_key")
    
    def __init__(self, value: Any):
        self.value = value
        self._cache_key = f"literal:{value!r}"
    
    def evaluate(self, facts: Dict[str, Any], cache: Dict[str, bool]) -> Any:
        return self.value
    
    def __repr__(self) -> str:
        return f"<Literal {self.value!r}>"


class Field(ASTNode):
    """Field reference node (variable lookup)."""
    
    __slots__ = ("field_name", "_cache_key")
    
    def __init__(self, field_name: str):
        self.field_name = field_name
        self._cache_key = f"field:{field_name}"
    
    def evaluate(self, facts: Dict[str, Any], cache: Dict[str, bool]) -> Any:
        return facts.get(self.field_name)
    
    def __repr__(self) -> str:
        return f"<Field {self.field_name}>"


# ============================================================================
# OPERATION NODES
# ============================================================================

class Comparison(ASTNode):
    """Comparison operation node (==, !=, >, <, in, etc.)."""
    
    __slots__ = ("left", "operator", "right", "_cache_key")
    
    def __init__(self, left: ASTNode, operator: str, right: ASTNode):
        self.left = left
        self.operator = operator
        self.right = right
        self._cache_key = f"comp:{operator}:{id(left)}:{id(right)}"
    
    def evaluate(self, facts: Dict[str, Any], cache: Dict[str, bool]) -> bool:
        if self._cache_key not in cache:
            left_val = self.left.evaluate(facts, cache)
            right_val = self.right.evaluate(facts, cache)
            
            # Handle null comparisons specially
            if self.operator in ["==", "!="]:
                if right_val is None or (isinstance(right_val, str) and right_val.lower() == "null"):
                    result = (left_val is None) if self.operator == "==" else (left_val is not None)
                elif left_val is None or (isinstance(left_val, str) and left_val.lower() == "null"):
                    result = (right_val is None) if self.operator == "==" else (right_val is not None)
                else:
                    result = _COMPARISON_OPS[self.operator](left_val, right_val)
            elif self.operator in _COMPARISON_OPS:
                result = _COMPARISON_OPS[self.operator](left_val, right_val)
            elif self.operator in _MEMBERSHIP_OPS:
                result = _MEMBERSHIP_OPS[self.operator](left_val, right_val)
            else:
                raise ValueError(f"Unknown comparison operator: {self.operator}")
            
            cache[self._cache_key] = bool(result)
        
        return cache[self._cache_key]
    
    def __repr__(self) -> str:
        return f"<Comparison {self.left} {self.operator} {self.right}>"


class Arithmetic(ASTNode):
    """Arithmetic operation node (+, -, *, /, %)."""
    
    __slots__ = ("left", "operator", "right", "_cache_key")
    
    def __init__(self, left: ASTNode, operator: str, right: ASTNode):
        self.left = left
        self.operator = operator
        self.right = right
        self._cache_key = f"arith:{operator}:{id(left)}:{id(right)}"
    
    def evaluate(self, facts: Dict[str, Any], cache: Dict[str, bool]) -> Any:
        if self._cache_key not in cache:
            left_val = self.left.evaluate(facts, cache)
            right_val = self.right.evaluate(facts, cache)
            
            if self.operator in _ARITHMETIC_OPS:
                result = _ARITHMETIC_OPS[self.operator](left_val, right_val)
            else:
                raise ValueError(f"Unknown arithmetic operator: {self.operator}")
            
            cache[self._cache_key] = result
        
        return cache[self._cache_key]
    
    def __repr__(self) -> str:
        return f"<Arithmetic {self.left} {self.operator} {self.right}>"


class Function(ASTNode):
    """Function call node (string helpers)."""
    
    __slots__ = ("function_name", "args", "_cache_key")
    
    def __init__(self, function_name: str, args: List[ASTNode]):
        self.function_name = function_name
        self.args = args
        self._cache_key = f"func:{function_name}:{len(args)}"
    
    def evaluate(self, facts: Dict[str, Any], cache: Dict[str, bool]) -> Any:
        cache_key = f"{self._cache_key}:{':'.join(str(id(arg)) for arg in self.args)}"
        
        if cache_key not in cache:
            if self.function_name in _STRING_FUNCTIONS:
                arg_values = [arg.evaluate(facts, cache) for arg in self.args]
                result = _STRING_FUNCTIONS[self.function_name](*arg_values)
            else:
                raise ValueError(f"Unknown function: {self.function_name}")
            
            cache[cache_key] = result
        
        return cache[cache_key]
    
    def __repr__(self) -> str:
        return f"<Function {self.function_name}({len(self.args)} args)>"


# ============================================================================
# BOOLEAN COMBINATOR NODES
# ============================================================================

class All(ASTNode):
    """Logical AND node - all children must be true."""
    
    __slots__ = ("children", "_cache_key")
    
    def __init__(self, *children: ASTNode):
        self.children = list(children)
        self._cache_key = f"all:{len(children)}"
    
    def evaluate(self, facts: Dict[str, Any], cache: Dict[str, bool]) -> bool:
        return all(child.evaluate(facts, cache) for child in self.children)
    
    def __repr__(self) -> str:
        return f"<All {len(self.children)} children>"


class Any(ASTNode):
    """Logical OR node - any child can be true."""
    
    __slots__ = ("children", "_cache_key")
    
    def __init__(self, *children: ASTNode):
        self.children = list(children)
        self._cache_key = f"any:{len(children)}"
    
    def evaluate(self, facts: Dict[str, Any], cache: Dict[str, bool]) -> bool:
        return any(child.evaluate(facts, cache) for child in self.children)
    
    def __repr__(self) -> str:
        return f"<Any {len(self.children)} children>"


class Not(ASTNode):
    """Logical NOT node - negates single child."""
    
    __slots__ = ("child", "_cache_key")
    
    def __init__(self, child: ASTNode):
        self.child = child
        self._cache_key = f"not:{id(child)}"
    
    def evaluate(self, facts: Dict[str, Any], cache: Dict[str, bool]) -> bool:
        return not self.child.evaluate(facts, cache)
    
    def __repr__(self) -> str:
        return f"<Not {self.child}>"


# ============================================================================
# LEGACY COMPATIBILITY ALIASES
# ============================================================================

# Maintain backward compatibility with old names
Expr = ASTNode
Pred = Comparison  # For simple field op value comparisons
And = All
Or = Any
