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
# EXPRESSION PARSER (merged from expressions.py)
# ============================================================================

import ast
import re


class ExpressionParser:
    """Parser that converts expressions to AST nodes."""
    
    def __init__(self):
        # Regex patterns for parsing
        self.comparison_pattern = re.compile(
            r"([a-zA-Z_][a-zA-Z0-9_\.]*)\s*(==|!=|>=|<=|>|<|in|not\s+in)\s*(.+)"
        )
        self.function_pattern = re.compile(
            r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*([^,]+)\s*,\s*(.+)\s*\)"
        )
        
    def parse(self, expression: Union[str, dict, list]) -> ASTNode:
        """Parse an expression into an AST node."""
        if isinstance(expression, str):
            return self._parse_string_expression(expression)
        elif isinstance(expression, dict):
            return self._parse_structured_expression(expression)
        elif isinstance(expression, list):
            return self._parse_expression_list(expression)
        else:
            raise ValueError(f"Unsupported expression type: {type(expression)}")
    
    def _parse_string_expression(self, expr: str) -> ASTNode:
        """Parse a string expression using Python AST."""
        try:
            # Use Python's AST parser for complex expressions
            tree = ast.parse(expr.strip(), mode="eval")
            return self._ast_to_node(tree.body)
        except SyntaxError:
            # Fall back to simple pattern matching for basic comparisons
            return self._parse_simple_comparison(expr)
    
    def _parse_simple_comparison(self, expr: str) -> ASTNode:
        """Parse simple comparison expressions."""
        expr = expr.strip()
        
        # Check for function calls
        func_match = self.function_pattern.match(expr)
        if func_match:
            func_name = func_match.group(1)
            arg1 = func_match.group(2).strip()
            arg2 = func_match.group(3).strip()
            
            return Function(
                function_name=func_name,
                args=[
                    self._parse_literal_or_field(arg1),
                    self._parse_literal_or_field(arg2)
                ]
            )
        
        # Check for comparison operators
        comp_match = self.comparison_pattern.match(expr)
        if comp_match:
            field = comp_match.group(1)
            op = comp_match.group(2).strip()
            value = comp_match.group(3).strip()
            
            return Comparison(
                left=Field(field),
                operator=op,
                right=self._parse_literal_or_field(value)
            )
        
        # Default to field reference
        return Field(expr)
    
    def _parse_structured_expression(self, expr_dict: dict) -> ASTNode:
        """Parse structured YAML expressions (all, any, not)."""
        if "all" in expr_dict:
            children = [self.parse(child) for child in expr_dict["all"]]
            return All(*children)
        elif "any" in expr_dict:
            children = [self.parse(child) for child in expr_dict["any"]]
            return Any(*children)
        elif "not" in expr_dict:
            child = self.parse(expr_dict["not"])
            return Not(child)
        else:
            raise ValueError(f"Unknown structured expression: {expr_dict}")
    
    def _parse_expression_list(self, expr_list: list) -> ASTNode:
        """Parse a list of expressions as an implicit AND."""
        children = [self.parse(expr) for expr in expr_list]
        return All(*children)
    
    def _ast_to_node(self, node: ast.AST) -> ASTNode:
        """Convert Python AST node to our AST node."""
        if isinstance(node, ast.BoolOp):
            return self._handle_bool_op(node)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return self._handle_not_op(node)
        elif isinstance(node, ast.Compare):
            return self._handle_compare_op(node)
        elif isinstance(node, ast.BinOp):
            return self._handle_binary_op(node)
        elif isinstance(node, ast.Call):
            return self._handle_function_call(node)
        elif isinstance(node, ast.Name):
            return self._handle_name_node(node)
        elif isinstance(node, ast.Constant):
            return Literal(node.value)
        elif isinstance(node, ast.List):
            return self._handle_list_literal(node)
        # Legacy Python < 3.8 support
        elif isinstance(node, ast.Num):
            return Literal(node.n)
        elif isinstance(node, ast.Str):
            return Literal(node.s)
        elif isinstance(node, ast.NameConstant):
            return Literal(node.value)
        else:
            raise ValueError(f"Unsupported AST node type: {type(node)}")
    
    def _handle_bool_op(self, node: ast.BoolOp) -> ASTNode:
        """Handle boolean operations (and, or)."""
        children = [self._ast_to_node(child) for child in node.values]
        if isinstance(node.op, ast.And):
            return All(*children)
        else:
            return Any(*children)
    
    def _handle_not_op(self, node: ast.UnaryOp) -> ASTNode:
        """Handle NOT operations."""
        child = self._ast_to_node(node.operand)
        return Not(child)
    
    def _handle_compare_op(self, node: ast.Compare) -> ASTNode:
        """Handle comparison operations."""
        left = self._ast_to_node(node.left)
        
        # Handle chained comparisons
        current_left = left
        for op, comparator in zip(node.ops, node.comparators):
            op_str = self._ast_op_to_string(op)
            right = self._ast_to_node(comparator)
            
            comp_node = Comparison(current_left, op_str, right)
            current_left = comp_node
        
        return current_left
    
    def _handle_binary_op(self, node: ast.BinOp) -> ASTNode:
        """Handle binary arithmetic operations."""
        left = self._ast_to_node(node.left)
        right = self._ast_to_node(node.right)
        op_str = self._ast_op_to_string(node.op)
        return Arithmetic(left, op_str, right)
    
    def _handle_function_call(self, node: ast.Call) -> ASTNode:
        """Handle function calls."""
        func_name = node.func.id if isinstance(node.func, ast.Name) else str(node.func)
        args = [self._ast_to_node(arg) for arg in node.args]
        return Function(func_name, args)
    
    def _handle_name_node(self, node: ast.Name) -> ASTNode:
        """Handle name nodes (variables, literals, fields)."""
        # Check for special literals first
        if node.id.lower() in ["null", "none"]:
            return Literal(None)
        elif node.id.lower() == "true":
            return Literal(True)
        elif node.id.lower() == "false":
            return Literal(False)
        else:
            return Field(node.id)
    
    def _handle_list_literal(self, node: ast.List) -> ASTNode:
        """Handle list literals [1, 2, 3] or ["a", "b", "c"]."""
        try:
            elements = []
            for elem in node.elts:
                if isinstance(elem, (ast.Constant, ast.Num, ast.Str, ast.NameConstant)):
                    elem_node = self._ast_to_node(elem)
                    elements.append(elem_node.value)
                else:
                    raise ValueError("Complex list element")
            return Literal(elements)
        except:
            raise ValueError(f"Complex list expressions not supported")
    
    def _ast_op_to_string(self, op: ast.operator) -> str:
        """Convert AST operator to string."""
        op_map = {
            ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=",
            ast.Gt: ">", ast.GtE: ">=", ast.In: "in", ast.NotIn: "not in",
            ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.Mod: "%",
        }
        return op_map.get(type(op), str(op))
    
    def _parse_literal_or_field(self, value: str) -> ASTNode:
        """Parse a literal value or field reference."""
        value = value.strip()
        
        # Handle quoted strings
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return Literal(value[1:-1])
        
        # Handle null (check this before field reference)
        if value.lower() in ["null", "none"]:
            return Literal(None)
        
        # Handle boolean
        if value.lower() == "true":
            return Literal(True)
        if value.lower() == "false":
            return Literal(False)
        
        # Handle numbers
        try:
            if "." in value:
                return Literal(float(value))
            else:
                return Literal(int(value))
        except ValueError:
            pass
        
        # Handle lists (for 'in' operator)
        if value.startswith("[") and value.endswith("]"):
            try:
                list_value = ast.literal_eval(value)
                return Literal(list_value)
            except (ValueError, SyntaxError):
                pass
        
        # Default to field reference
        return Field(value)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def parse_expression(expression: Union[str, dict, list]) -> ASTNode:
    """Parse an expression into an AST node."""
    parser = ExpressionParser()
    return parser.parse(expression)


def evaluate_expression(expression: Union[str, dict, list], facts: Dict[str, Any]) -> bool:
    """Parse and evaluate an expression against facts using AST."""
    ast_node = parse_expression(expression)
    cache: Dict[str, bool] = {}
    result = ast_node.evaluate(facts, cache)
    return bool(result)


# ============================================================================
# LEGACY COMPATIBILITY ALIASES
# ============================================================================

# Maintain backward compatibility with old names
Expr = ASTNode
Pred = Comparison  # For simple field op value comparisons
And = All
Or = Any
