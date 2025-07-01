"""
symbolica.compiler.expressions
==============================

Comprehensive expression parser for Symbolica rule conditions.

Supports 6 categories of expressions:
1. Boolean combinators   - all:, any:, not:
2. Comparison operators  - ==, !=, >, >=, <, <=  
3. Membership/containment - in, not in
4. String helpers        - startswith(), endswith(), contains()
5. Arithmetic           - +, -, *, /, %, parentheses
6. Null/missing checks  - field == null, field != null

Expression formats:
- String expressions: "transaction_amount > 1000"
- YAML structured: { all: [...], any: [...], not: ... }
- Mixed: [ "amount > 1000", { any: [...] } ]
"""

from __future__ import annotations

import ast
import operator
import re
from typing import Any, Dict, List, Union, Callable
from dataclasses import dataclass


# ============================================================================
# EXPRESSION EVALUATION OPERATORS
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

_STRING_HELPERS = {
    "startswith": _startswith,
    "endswith": _endswith, 
    "contains": _contains,
}


# ============================================================================
# AST NODE CLASSES FOR EXPRESSION TREE
# ============================================================================

@dataclass
class ExpressionNode:
    """Base class for expression tree nodes."""
    
    def evaluate(self, facts: Dict[str, Any]) -> Any:
        """Evaluate this node against the given facts."""
        raise NotImplementedError


@dataclass 
class LiteralNode(ExpressionNode):
    """Literal value node (number, string, boolean, null)."""
    value: Any
    
    def evaluate(self, facts: Dict[str, Any]) -> Any:
        return self.value


@dataclass
class FieldNode(ExpressionNode):
    """Field reference node (variable lookup)."""
    field_name: str
    
    def evaluate(self, facts: Dict[str, Any]) -> Any:
        return facts.get(self.field_name)


@dataclass
class ComparisonNode(ExpressionNode):
    """Comparison operation node."""
    left: ExpressionNode
    operator: str
    right: ExpressionNode
    
    def evaluate(self, facts: Dict[str, Any]) -> Any:
        left_val = self.left.evaluate(facts)
        right_val = self.right.evaluate(facts)
        
        # Handle null comparisons specially
        if self.operator in ["==", "!="]:
            if right_val is None or (isinstance(right_val, str) and right_val.lower() == "null"):
                return (left_val is None) if self.operator == "==" else (left_val is not None)
            if left_val is None or (isinstance(left_val, str) and left_val.lower() == "null"):
                return (right_val is None) if self.operator == "==" else (right_val is not None)
        
        # Regular comparison operations
        if self.operator in _COMPARISON_OPS:
            return _COMPARISON_OPS[self.operator](left_val, right_val)
        elif self.operator in _MEMBERSHIP_OPS:
            return _MEMBERSHIP_OPS[self.operator](left_val, right_val)
        else:
            raise ValueError(f"Unknown comparison operator: {self.operator}")


@dataclass
class ArithmeticNode(ExpressionNode):
    """Arithmetic operation node."""
    left: ExpressionNode
    operator: str
    right: ExpressionNode
    
    def evaluate(self, facts: Dict[str, Any]) -> Any:
        left_val = self.left.evaluate(facts)
        right_val = self.right.evaluate(facts)
        
        if self.operator in _ARITHMETIC_OPS:
            return _ARITHMETIC_OPS[self.operator](left_val, right_val)
        else:
            raise ValueError(f"Unknown arithmetic operator: {self.operator}")


@dataclass
class FunctionCallNode(ExpressionNode):
    """Function call node (string helpers)."""
    function_name: str
    args: List[ExpressionNode]
    
    def evaluate(self, facts: Dict[str, Any]) -> Any:
        if self.function_name in _STRING_HELPERS:
            arg_values = [arg.evaluate(facts) for arg in self.args]
            return _STRING_HELPERS[self.function_name](*arg_values)
        else:
            raise ValueError(f"Unknown function: {self.function_name}")


@dataclass
class BooleanNode(ExpressionNode):
    """Boolean combinator node (all, any, not)."""
    operator: str  # "all", "any", "not"
    children: List[ExpressionNode]
    
    def evaluate(self, facts: Dict[str, Any]) -> Any:
        if self.operator == "all":
            return all(child.evaluate(facts) for child in self.children)
        elif self.operator == "any":
            return any(child.evaluate(facts) for child in self.children)
        elif self.operator == "not":
            if len(self.children) != 1:
                raise ValueError("NOT operator requires exactly one child")
            return not self.children[0].evaluate(facts)
        else:
            raise ValueError(f"Unknown boolean operator: {self.operator}")


# ============================================================================
# EXPRESSION PARSER
# ============================================================================

class ExpressionParser:
    """Parser for Symbolica rule expressions."""
    
    def __init__(self):
        # Regex patterns for parsing
        self.comparison_pattern = re.compile(
            r"([a-zA-Z_][a-zA-Z0-9_\.]*)\s*(==|!=|>=|<=|>|<|in|not\s+in)\s*(.+)"
        )
        self.function_pattern = re.compile(
            r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*([^,]+)\s*,\s*(.+)\s*\)"
        )
        
    def parse(self, expression: Union[str, dict, list]) -> ExpressionNode:
        """Parse an expression into an expression tree."""
        if isinstance(expression, str):
            return self._parse_string_expression(expression)
        elif isinstance(expression, dict):
            return self._parse_structured_expression(expression)
        elif isinstance(expression, list):
            return self._parse_expression_list(expression)
        else:
            raise ValueError(f"Unsupported expression type: {type(expression)}")
    
    def _parse_string_expression(self, expr: str) -> ExpressionNode:
        """Parse a string expression using Python AST."""
        try:
            # Use Python's AST parser for complex expressions
            tree = ast.parse(expr.strip(), mode="eval")
            return self._ast_to_expression_node(tree.body)
        except SyntaxError:
            # Fall back to simple pattern matching for basic comparisons
            return self._parse_simple_comparison(expr)
    
    def _parse_simple_comparison(self, expr: str) -> ExpressionNode:
        """Parse simple comparison expressions."""
        expr = expr.strip()
        
        # Check for function calls
        func_match = self.function_pattern.match(expr)
        if func_match:
            func_name = func_match.group(1)
            arg1 = func_match.group(2).strip()
            arg2 = func_match.group(3).strip()
            
            return FunctionCallNode(
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
            
            return ComparisonNode(
                left=FieldNode(field),
                operator=op,
                right=self._parse_literal_or_field(value)
            )
        
        # Default to field reference
        return FieldNode(expr)
    
    def _parse_structured_expression(self, expr_dict: dict) -> ExpressionNode:
        """Parse structured YAML expressions (all, any, not)."""
        if "all" in expr_dict:
            children = [self.parse(child) for child in expr_dict["all"]]
            return BooleanNode("all", children)
        elif "any" in expr_dict:
            children = [self.parse(child) for child in expr_dict["any"]]
            return BooleanNode("any", children)
        elif "not" in expr_dict:
            child = self.parse(expr_dict["not"])
            return BooleanNode("not", [child])
        else:
            raise ValueError(f"Unknown structured expression: {expr_dict}")
    
    def _parse_expression_list(self, expr_list: list) -> ExpressionNode:
        """Parse a list of expressions as an implicit AND."""
        children = [self.parse(expr) for expr in expr_list]
        return BooleanNode("all", children)
    
    def _ast_to_expression_node(self, node: ast.AST) -> ExpressionNode:
        """Convert Python AST node to ExpressionNode."""
        if isinstance(node, ast.BoolOp):
            op_name = "all" if isinstance(node.op, ast.And) else "any"
            children = [self._ast_to_expression_node(child) for child in node.values]
            return BooleanNode(op_name, children)
        
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            child = self._ast_to_expression_node(node.operand)
            return BooleanNode("not", [child])
        
        elif isinstance(node, ast.Compare):
            left = self._ast_to_expression_node(node.left)
            
            # Handle chained comparisons
            current_left = left
            for op, comparator in zip(node.ops, node.comparators):
                op_str = self._ast_op_to_string(op)
                right = self._ast_to_expression_node(comparator)
                
                comp_node = ComparisonNode(current_left, op_str, right)
                current_left = comp_node
            
            return current_left
        
        elif isinstance(node, ast.BinOp):
            left = self._ast_to_expression_node(node.left)
            right = self._ast_to_expression_node(node.right)
            op_str = self._ast_op_to_string(node.op)
            return ArithmeticNode(left, op_str, right)
        
        elif isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else str(node.func)
            args = [self._ast_to_expression_node(arg) for arg in node.args]
            return FunctionCallNode(func_name, args)
        
        elif isinstance(node, ast.Name):
            return FieldNode(node.id)
        
        elif isinstance(node, ast.Constant):
            return LiteralNode(node.value)
        
        elif isinstance(node, ast.List):
            # Handle list literals [1, 2, 3] or ["a", "b", "c"]
            # For simple literals only, create a LiteralNode
            try:
                elements = []
                for elem in node.elts:
                    if isinstance(elem, (ast.Constant, ast.Num, ast.Str, ast.NameConstant)):
                        elem_node = self._ast_to_expression_node(elem)
                        elements.append(elem_node.value)
                    else:
                        # Complex element, can't evaluate as simple literal
                        raise ValueError("Complex list element")
                return LiteralNode(elements)
            except:
                # Fall back to error for complex lists
                raise ValueError(f"Complex list expressions not supported in this context")
        
        elif isinstance(node, ast.Tuple):
            # Handle tuple literals (1, 2, 3)
            try:
                elements = []
                for elem in node.elts:
                    if isinstance(elem, (ast.Constant, ast.Num, ast.Str, ast.NameConstant)):
                        elem_node = self._ast_to_expression_node(elem)
                        elements.append(elem_node.value)
                    else:
                        raise ValueError("Complex tuple element")
                return LiteralNode(tuple(elements))
            except:
                raise ValueError(f"Complex tuple expressions not supported in this context")
        
        elif isinstance(node, ast.Dict):
            # Handle dictionary literals for YAML structures { all: [...] }
            # This is a fallback - structured YAML should be handled by _parse_structured_expression
            raise ValueError(f"Dictionary expressions should be handled as structured YAML, not AST")
        
        # Legacy Python < 3.8 support
        elif isinstance(node, ast.Num):
            return LiteralNode(node.n)
        elif isinstance(node, ast.Str):
            return LiteralNode(node.s)
        elif isinstance(node, ast.NameConstant):
            return LiteralNode(node.value)
        
        else:
            raise ValueError(f"Unsupported AST node type: {type(node)}")
    
    def _ast_op_to_string(self, op: ast.operator) -> str:
        """Convert AST operator to string."""
        op_map = {
            ast.Eq: "==",
            ast.NotEq: "!=", 
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.Gt: ">",
            ast.GtE: ">=",
            ast.In: "in",
            ast.NotIn: "not in",
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.Mod: "%",
        }
        return op_map.get(type(op), str(op))
    
    def _parse_literal_or_field(self, value: str) -> ExpressionNode:
        """Parse a literal value or field reference."""
        value = value.strip()
        
        # Handle quoted strings
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return LiteralNode(value[1:-1])
        
        # Handle null
        if value.lower() in ["null", "none"]:
            return LiteralNode(None)
        
        # Handle boolean
        if value.lower() == "true":
            return LiteralNode(True)
        if value.lower() == "false":
            return LiteralNode(False)
        
        # Handle numbers
        try:
            if "." in value:
                return LiteralNode(float(value))
            else:
                return LiteralNode(int(value))
        except ValueError:
            pass
        
        # Handle lists (for 'in' operator)
        if value.startswith("[") and value.endswith("]"):
            try:
                list_value = ast.literal_eval(value)
                return LiteralNode(list_value)
            except (ValueError, SyntaxError):
                pass
        
        # Default to field reference
        return FieldNode(value)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def parse_expression(expression: Union[str, dict, list]) -> ExpressionNode:
    """Parse an expression into an expression tree."""
    parser = ExpressionParser()
    return parser.parse(expression)


def evaluate_expression(expression: Union[str, dict, list], facts: Dict[str, Any]) -> bool:
    """Parse and evaluate an expression against facts."""
    expr_tree = parse_expression(expression)
    result = expr_tree.evaluate(facts)
    return bool(result)


 