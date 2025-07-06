"""
High-Performance Condition Evaluator
====================================

Comprehensive AST-based expression evaluation with support for:
- String expressions (Python-like syntax)
- Structured YAML expressions (all/any/not combinators)
- Boolean combinators, comparison operators, arithmetic
- String functions, null checks, nested expressions
- Content-based caching for performance
"""

import ast
import hashlib
import re
from typing import Dict, Any, FrozenSet, Optional, Set, Union, List
from functools import lru_cache
import time

from ..core import (
    Condition, ExecutionContext, ConditionEvaluator, 
    EvaluationError, condition
)


# Pre-compiled patterns for performance
FIELD_PATTERN = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b')
RESERVED_WORDS = frozenset({
    'True', 'False', 'None', 'and', 'or', 'not', 'in', 'is',
    'if', 'else', 'elif', 'for', 'while', 'def', 'class', 'import',
    'null', 'true', 'false'  # Added YAML literals
})


class ComprehensiveConditionEvaluator(ConditionEvaluator):
    """
    Comprehensive condition evaluator supporting multiple expression formats.
    
    Features:
    - String expressions: "amount > 1000 and status == 'active'"
    - Structured YAML: {all: ["amount > 1000", "status == 'active'"]}
    - Boolean combinators: all, any, not
    - Comparison operators: ==, !=, >, >=, <, <=, in, not in
    - Arithmetic operations: +, -, *, /, %, **
    - String functions: startswith, endswith, contains, matches
    - Null checks: field == null, field != null
    - Content-based caching for performance
    """
    
    def __init__(self):
        # Cache for parsed expressions (content-based keys)
        self._expression_cache: Dict[str, Any] = {}
        # Cache for field extraction
        self._field_cache: Dict[str, FrozenSet[str]] = {}
        # Built-in functions
        self._functions = self._create_comprehensive_function_registry()
    
    def evaluate(self, condition: Condition, context: ExecutionContext) -> bool:
        """
        Evaluate condition against context with comprehensive support.
        
        Supports both string expressions and structured YAML expressions.
        """
        cache_key = f"eval:{condition.content_hash}"
        
        # Check context cache first
        if cache_key in context.enriched_facts:
            return context.enriched_facts[cache_key]
        
        try:
            # Parse expression (handles both string and structured formats)
            parsed_expr = self._parse_expression(condition.expression)
            
            # Evaluate parsed expression
            result = self._evaluate_expression(parsed_expr, context.enriched_facts)
            
            # Cache result using content hash
            context.enriched_facts[cache_key] = bool(result)
            return context.enriched_facts[cache_key]
            
        except Exception as e:
            raise EvaluationError(
                f"Failed to evaluate expression: {e}",
                expression=condition.expression,
                rule_id=getattr(context, 'current_rule_id', None)
            ) from e
    
    def extract_fields(self, condition: Condition) -> FrozenSet[str]:
        """
        Extract field names from both string and structured expressions.
        """
        if condition.content_hash in self._field_cache:
            return self._field_cache[condition.content_hash]
        
        try:
            # Parse expression to extract fields
            parsed_expr = self._parse_expression(condition.expression)
            
            # Extract field names
            fields = set()
            self._extract_fields_from_expression(parsed_expr, fields)
            
            # Remove reserved words and built-in functions
            clean_fields = fields - RESERVED_WORDS - set(self._functions.keys())
            result = frozenset(clean_fields)
            
            # Cache result
            self._field_cache[condition.content_hash] = result
            
            # Update condition object with extracted fields
            if not condition.referenced_fields:
                object.__setattr__(condition, 'referenced_fields', result)
            
            return result
            
        except Exception:
            # Fallback to regex extraction
            return self._extract_fields_regex(condition.expression)
    
    def _parse_expression(self, expression: Union[str, dict, list]) -> Any:
        """
        Parse expression into evaluable format.
        Supports string expressions, structured YAML, and lists.
        """
        if isinstance(expression, str):
            return self._parse_string_expression(expression)
        elif isinstance(expression, dict):
            return self._parse_structured_expression(expression)
        elif isinstance(expression, list):
            return self._parse_list_expression(expression)
        else:
            return expression
    
    def _parse_string_expression(self, expr: str) -> ast.AST:
        """Parse string expression using Python AST."""
        expr = expr.strip()
        
        # Handle null comparisons
        expr = self._normalize_null_expressions(expr)
        
        try:
            tree = ast.parse(expr, mode='eval')
            return tree.body
        except SyntaxError as e:
            raise EvaluationError(
                f"Invalid expression syntax: {e}",
                expression=expr
            ) from e
    
    def _parse_structured_expression(self, expr: dict) -> dict:
        """Parse structured YAML expression (all/any/not combinators)."""
        # Handle boolean combinators
        if 'all' in expr:
            return {
                'type': 'all',
                'children': [self._parse_expression(child) for child in expr['all']]
            }
        elif 'any' in expr:
            return {
                'type': 'any', 
                'children': [self._parse_expression(child) for child in expr['any']]
            }
        elif 'not' in expr:
            return {
                'type': 'not',
                'child': self._parse_expression(expr['not'])
            }
        else:
            # Handle comparison objects
            return self._parse_comparison_object(expr)
    
    def _parse_list_expression(self, expr: list) -> dict:
        """Parse list expression as implicit AND."""
        return {
            'type': 'all',
            'children': [self._parse_expression(child) for child in expr]
        }
    
    def _parse_comparison_object(self, expr: dict) -> dict:
        """Parse comparison object format."""
        # Handle formats like {"field": "value"} or {"field": {"$gt": 10}}
        if len(expr) == 1:
            field, value = next(iter(expr.items()))
            if isinstance(value, dict) and len(value) == 1:
                # MongoDB-style operators
                operator, operand = next(iter(value.items()))
                return {
                    'type': 'comparison',
                    'field': field,
                    'operator': operator,
                    'value': operand
                }
            else:
                # Simple equality
                return {
                    'type': 'comparison',
                    'field': field,
                    'operator': '==',
                    'value': value
                }
        else:
            raise EvaluationError(f"Invalid comparison object: {expr}")
    
    def _normalize_null_expressions(self, expr: str) -> str:
        """Normalize null expressions to Python None."""
        # Replace null with None for Python compatibility
        expr = re.sub(r'\bnull\b', 'None', expr)
        return expr
    
    def _evaluate_expression(self, expr: Any, facts: Dict[str, Any]) -> Any:
        """Evaluate parsed expression."""
        if isinstance(expr, ast.AST):
            return self._evaluate_ast_node(expr, facts)
        elif isinstance(expr, dict):
            return self._evaluate_structured_expression(expr, facts)
        else:
            return expr
    
    def _evaluate_structured_expression(self, expr: dict, facts: Dict[str, Any]) -> bool:
        """Evaluate structured expression (all/any/not combinators)."""
        expr_type = expr.get('type')
        
        if expr_type == 'all':
            return all(self._evaluate_expression(child, facts) for child in expr['children'])
        elif expr_type == 'any':
            return any(self._evaluate_expression(child, facts) for child in expr['children'])
        elif expr_type == 'not':
            return not self._evaluate_expression(expr['child'], facts)
        elif expr_type == 'comparison':
            return self._evaluate_comparison_object(expr, facts)
        else:
            raise EvaluationError(f"Unknown expression type: {expr_type}")
    
    def _evaluate_comparison_object(self, expr: dict, facts: Dict[str, Any]) -> bool:
        """Evaluate comparison object."""
        field = expr['field']
        operator = expr['operator']
        value = expr['value']
        
        field_value = facts.get(field)
        
        try:
            if operator == '==' or operator == '$eq':
                return field_value == value
            elif operator == '!=' or operator == '$ne':
                return field_value != value
            elif operator == '>' or operator == '$gt':
                return field_value > value
            elif operator == '>=' or operator == '$gte':
                return field_value >= value
            elif operator == '<' or operator == '$lt':
                return field_value < value
            elif operator == '<=' or operator == '$lte':
                return field_value <= value
            elif operator == 'in' or operator == '$in':
                return field_value in value if value is not None else False
            elif operator == 'not in' or operator == '$nin':
                return field_value not in value if value is not None else True
            else:
                raise EvaluationError(f"Unknown comparison operator: {operator}")
        except (TypeError, ValueError):
            return False
    
    def _evaluate_ast_node(self, node: ast.AST, facts: Dict[str, Any]) -> Any:
        """Evaluate AST node with comprehensive support."""
        
        if isinstance(node, ast.BoolOp):
            return self._evaluate_bool_op(node, facts)
        
        elif isinstance(node, ast.UnaryOp):
            return self._evaluate_unary_op(node, facts)
        
        elif isinstance(node, ast.Compare):
            return self._evaluate_compare(node, facts)
        
        elif isinstance(node, ast.BinOp):
            return self._evaluate_bin_op(node, facts)
        
        elif isinstance(node, ast.Call):
            return self._evaluate_call(node, facts)
        
        elif isinstance(node, ast.Name):
            return facts.get(node.id)
        
        elif isinstance(node, ast.Constant):
            return node.value
        
        # Legacy Python < 3.8 support
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.NameConstant):
            return node.value
        elif isinstance(node, ast.List):
            return [self._evaluate_ast_node(elem, facts) for elem in node.elts]
        
        else:
            raise EvaluationError(f"Unsupported AST node type: {type(node)}")
    
    def _evaluate_bool_op(self, node: ast.BoolOp, facts: Dict[str, Any]) -> bool:
        """Evaluate boolean operation with short-circuiting."""
        if isinstance(node.op, ast.And):
            # Short-circuit AND
            for value in node.values:
                if not self._evaluate_ast_node(value, facts):
                    return False
            return True
        else:  # Or
            # Short-circuit OR
            for value in node.values:
                if self._evaluate_ast_node(value, facts):
                    return True
            return False
    
    def _evaluate_unary_op(self, node: ast.UnaryOp, facts: Dict[str, Any]) -> Any:
        """Evaluate unary operation."""
        operand = self._evaluate_ast_node(node.operand, facts)
        
        if isinstance(node.op, ast.Not):
            return not operand
        elif isinstance(node.op, ast.UAdd):
            return +operand
        elif isinstance(node.op, ast.USub):
            return -operand
        else:
            raise EvaluationError(f"Unsupported unary operator: {type(node.op)}")
    
    def _evaluate_compare(self, node: ast.Compare, facts: Dict[str, Any]) -> bool:
        """Evaluate comparison with proper null handling."""
        left = self._evaluate_ast_node(node.left, facts)
        
        # Handle chained comparisons
        for op, comparator in zip(node.ops, node.comparators):
            right = self._evaluate_ast_node(comparator, facts)
            
            if not self._compare_values(left, op, right):
                return False
            
            left = right  # For chained comparisons like a < b < c
        
        return True
    
    def _compare_values(self, left: Any, op: ast.cmpop, right: Any) -> bool:
        """Compare two values with safe handling."""
        try:
            if isinstance(op, ast.Eq):
                return left == right
            elif isinstance(op, ast.NotEq):
                return left != right
            elif isinstance(op, ast.Lt):
                return left < right
            elif isinstance(op, ast.LtE):
                return left <= right
            elif isinstance(op, ast.Gt):
                return left > right
            elif isinstance(op, ast.GtE):
                return left >= right
            elif isinstance(op, ast.In):
                return left in right if right is not None else False
            elif isinstance(op, ast.NotIn):
                return left not in right if right is not None else True
            elif isinstance(op, ast.Is):
                return left is right
            elif isinstance(op, ast.IsNot):
                return left is not right
            else:
                raise EvaluationError(f"Unsupported comparison operator: {type(op)}")
        
        except (TypeError, ValueError):
            # Incompatible types for comparison
            return False
    
    def _evaluate_bin_op(self, node: ast.BinOp, facts: Dict[str, Any]) -> Any:
        """Evaluate binary operation safely."""
        left = self._evaluate_ast_node(node.left, facts)
        right = self._evaluate_ast_node(node.right, facts)
        
        try:
            if isinstance(node.op, ast.Add):
                return left + right
            elif isinstance(node.op, ast.Sub):
                return left - right
            elif isinstance(node.op, ast.Mult):
                return left * right
            elif isinstance(node.op, ast.Div):
                return left / right if right != 0 else float('inf')
            elif isinstance(node.op, ast.FloorDiv):
                return left // right if right != 0 else float('inf')
            elif isinstance(node.op, ast.Mod):
                return left % right if right != 0 else 0
            elif isinstance(node.op, ast.Pow):
                return left ** right
            else:
                raise EvaluationError(f"Unsupported binary operator: {type(node.op)}")
        
        except (TypeError, ValueError, ZeroDivisionError):
            return None
    
    def _evaluate_call(self, node: ast.Call, facts: Dict[str, Any]) -> Any:
        """Evaluate function call safely."""
        func_name = node.func.id if isinstance(node.func, ast.Name) else str(node.func)
        
        if func_name not in self._functions:
            raise EvaluationError(f"Unknown function: {func_name}")
        
        # Evaluate arguments
        args = [self._evaluate_ast_node(arg, facts) for arg in node.args]
        
        try:
            return self._functions[func_name](*args)
        except Exception as e:
            raise EvaluationError(f"Function '{func_name}' failed: {e}") from e
    
    def _extract_fields_from_expression(self, expr: Any, fields: Set[str]) -> None:
        """Extract field names from parsed expression."""
        if isinstance(expr, ast.AST):
            self._extract_names_from_ast(expr, fields)
        elif isinstance(expr, dict):
            self._extract_fields_from_structured(expr, fields)
    
    def _extract_fields_from_structured(self, expr: dict, fields: Set[str]) -> None:
        """Extract fields from structured expression."""
        expr_type = expr.get('type')
        
        if expr_type in ['all', 'any']:
            for child in expr['children']:
                self._extract_fields_from_expression(child, fields)
        elif expr_type == 'not':
            self._extract_fields_from_expression(expr['child'], fields)
        elif expr_type == 'comparison':
            fields.add(expr['field'])
    
    def _extract_names_from_ast(self, node: ast.AST, fields: Set[str]) -> None:
        """Extract field names from AST recursively."""
        if isinstance(node, ast.Name):
            fields.add(node.id)
        
        # Recursively process child nodes
        for child in ast.iter_child_nodes(node):
            self._extract_names_from_ast(child, fields)
    
    def _extract_fields_regex(self, expression: str) -> FrozenSet[str]:
        """Fallback field extraction using regex."""
        if isinstance(expression, str):
            matches = FIELD_PATTERN.findall(expression)
        else:
            matches = []
        clean_fields = {m for m in matches if m not in RESERVED_WORDS}
        return frozenset(clean_fields)
    
    def _create_comprehensive_function_registry(self) -> Dict[str, callable]:
        """Create comprehensive registry of built-in functions."""
        return {
            # Type conversion
            'str': lambda x: str(x) if x is not None else '',
            'int': lambda x: int(x) if x is not None else 0,
            'float': lambda x: float(x) if x is not None else 0.0,
            'bool': lambda x: bool(x),
            
            # Length and size
            'len': lambda x: len(x) if x is not None else 0,
            'length': lambda x: len(x) if x is not None else 0,
            
            # String functions (comprehensive)
            'lower': lambda x: str(x or '').lower(),
            'upper': lambda x: str(x or '').upper(),
            'strip': lambda x: str(x or '').strip(),
            'startswith': lambda text, prefix: str(text or '').startswith(str(prefix or '')),
            'endswith': lambda text, suffix: str(text or '').endswith(str(suffix or '')),
            'contains': lambda text, substr: str(substr or '') in str(text or ''),
            'matches': lambda text, pattern: re.search(str(pattern or ''), str(text or '')) is not None,
            'split': lambda text, sep=' ': str(text or '').split(str(sep)),
            'join': lambda sep, items: str(sep).join(str(item) for item in (items or [])),
            'replace': lambda text, old, new: str(text or '').replace(str(old or ''), str(new or '')),
            
            # Math functions
            'abs': lambda x: abs(x) if x is not None else 0,
            'max': lambda *args: max(arg for arg in args if arg is not None) if args else None,
            'min': lambda *args: min(arg for arg in args if arg is not None) if args else None,
            'round': lambda x, n=0: round(x, n) if x is not None else 0,
            'ceil': lambda x: int(x) + (1 if x > int(x) else 0) if x is not None else 0,
            'floor': lambda x: int(x) if x is not None else 0,
            
            # List functions
            'sum': lambda x: sum(x) if x is not None else 0,
            'any': lambda x: any(x) if x is not None else False,
            'all': lambda x: all(x) if x is not None else True,
            'count': lambda x: len(x) if x is not None else 0,
            
            # Date/time functions (basic)
            'now': lambda: int(time.time()),
            'today': lambda: int(time.time()) // 86400,
            
            # Null/existence checks
            'is_null': lambda x: x is None,
            'is_not_null': lambda x: x is not None,
            'is_empty': lambda x: not x if x is not None else True,
            'is_not_empty': lambda x: bool(x) if x is not None else False,
        }
    
    def register_function(self, name: str, func: callable) -> None:
        """Register custom function."""
        self._functions[name] = func


# Factory function - use comprehensive evaluator by default
def create_evaluator() -> ComprehensiveConditionEvaluator:
    """Create comprehensive condition evaluator."""
    return ComprehensiveConditionEvaluator()


# Legacy alias for backward compatibility
ASTConditionEvaluator = ComprehensiveConditionEvaluator 