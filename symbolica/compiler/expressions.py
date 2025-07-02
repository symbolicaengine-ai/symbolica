"""
symbolica.compiler.expressions
==============================

Expression parser that builds AST nodes for Symbolica rule conditions.

This module parses various expression formats and converts them to AST nodes
from symbolica.compiler.ast for evaluation.
"""

from __future__ import annotations

import ast
import re
from typing import Any, Dict, List, Union

# Import the unified AST system
from .ast import (
    ASTNode, Literal, Field, Comparison, Arithmetic, Function, All, Any, Not
)


# ============================================================================
# EXPRESSION PARSER
# ============================================================================

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
            children = [self._ast_to_node(child) for child in node.values]
            if isinstance(node.op, ast.And):
                return All(*children)
            else:
                return Any(*children)
        
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            child = self._ast_to_node(node.operand)
            return Not(child)
        
        elif isinstance(node, ast.Compare):
            left = self._ast_to_node(node.left)
            
            # Handle chained comparisons
            current_left = left
            for op, comparator in zip(node.ops, node.comparators):
                op_str = self._ast_op_to_string(op)
                right = self._ast_to_node(comparator)
                
                comp_node = Comparison(current_left, op_str, right)
                current_left = comp_node
            
            return current_left
        
        elif isinstance(node, ast.BinOp):
            left = self._ast_to_node(node.left)
            right = self._ast_to_node(node.right)
            op_str = self._ast_op_to_string(node.op)
            return Arithmetic(left, op_str, right)
        
        elif isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else str(node.func)
            args = [self._ast_to_node(arg) for arg in node.args]
            return Function(func_name, args)
        
        elif isinstance(node, ast.Name):
            # Check for special literals first
            if node.id.lower() in ["null", "none"]:
                return Literal(None)
            elif node.id.lower() == "true":
                return Literal(True)
            elif node.id.lower() == "false":
                return Literal(False)
            else:
                return Field(node.id)
        
        elif isinstance(node, ast.Constant):
            return Literal(node.value)
        
        elif isinstance(node, ast.List):
            # Handle list literals [1, 2, 3] or ["a", "b", "c"]
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
        
        # Legacy Python < 3.8 support
        elif isinstance(node, ast.Num):
            return Literal(node.n)
        elif isinstance(node, ast.Str):
            return Literal(node.s)
        elif isinstance(node, ast.NameConstant):
            return Literal(node.value)
        
        else:
            raise ValueError(f"Unsupported AST node type: {type(node)}")
    
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


 