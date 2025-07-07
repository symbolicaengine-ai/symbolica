"""
AST-Based Expression Evaluator
==============================

Fast AST-based expression evaluation for deterministic AI agent reasoning.

Features:
- Python-like expression syntax
- Safe AST evaluation (no eval() vulnerabilities)
- Simple caching for performance
- Field extraction for DAG dependency analysis
"""

import ast
import re
from typing import Dict, Any, Set, Union, List
from functools import lru_cache

from ..core import ExecutionContext, ConditionEvaluator, EvaluationError


# Pre-compiled patterns for performance
FIELD_PATTERN = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b')
RESERVED_WORDS = frozenset({
    'True', 'False', 'None', 'and', 'or', 'not', 'in', 'is',
    'len', 'sum', 'max', 'min', 'abs', 'str', 'int', 'float'
})


class SimpleConditionEvaluator(ConditionEvaluator):
    """
    Simple, fast condition evaluator for AI agents.
    
    Supports:
    - Basic comparisons: ==, !=, >, >=, <, <=, in, not in
    - Boolean operators: and, or, not
    - Arithmetic: +, -, *, /, %
    - Basic functions: len, sum, max, min, abs
    - Null checks: == None, != None
    """
    
    def __init__(self):
        # Simple LRU cache for parsed expressions
        self._ast_cache: Dict[str, ast.AST] = {}
        self._field_cache: Dict[str, Set[str]] = {}
        self._max_cache_size = 1000
        
        # Built-in functions
        self._functions = {
            'len': len,
            'sum': sum,
            'max': max,
            'min': min,
            'abs': abs,
            'str': str,
            'int': int,
            'float': float,
        }
    
    def evaluate(self, condition_expr: str, context: ExecutionContext) -> bool:
        """Evaluate condition expression against context."""
        try:
            # Get or parse AST
            ast_node = self._get_or_parse_ast(condition_expr)
            
            # Evaluate against enriched facts
            result = self._evaluate_ast_node(ast_node, context.enriched_facts)
            
            return bool(result)
            
        except Exception as e:
            raise EvaluationError(
                f"Failed to evaluate expression: {e}",
                expression=condition_expr
            ) from e
    
    def extract_fields(self, condition_expr: str) -> Set[str]:
        """Extract field names referenced by the condition."""
        if condition_expr in self._field_cache:
            return self._field_cache[condition_expr]
        
        try:
            # Parse expression
            ast_node = self._get_or_parse_ast(condition_expr)
            
            # Extract field names
            fields = set()
            self._extract_names_from_ast(ast_node, fields)
            
            # Remove reserved words and functions
            clean_fields = fields - RESERVED_WORDS - set(self._functions.keys())
            result = clean_fields
            
            # Cache result (with size limit)
            if len(self._field_cache) < self._max_cache_size:
                self._field_cache[condition_expr] = result
            
            return result
            
        except Exception:
            # Fallback to regex extraction
            return self._extract_fields_regex(condition_expr)
    
    def _get_or_parse_ast(self, expression: str) -> ast.AST:
        """Get cached AST or parse new one."""
        if expression in self._ast_cache:
            return self._ast_cache[expression]
        
        try:
            # Normalize null expressions
            normalized = re.sub(r'\bnull\b', 'None', expression)
            
            # Parse to AST
            tree = ast.parse(normalized.strip(), mode='eval')
            ast_node = tree.body
            
            # Cache with size limit
            if len(self._ast_cache) < self._max_cache_size:
                self._ast_cache[expression] = ast_node
            
            return ast_node
            
        except SyntaxError as e:
            raise EvaluationError(f"Invalid expression syntax: {e}") from e
    
    def _evaluate_ast_node(self, node: ast.AST, facts: Dict[str, Any]) -> Any:
        """Evaluate AST node."""
        # Use visitor pattern for clean evaluation
        if isinstance(node, ast.Name):
            return facts.get(node.id)
        
        elif isinstance(node, ast.Constant):
            return node.value
        
        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(self._evaluate_ast_node(value, facts) for value in node.values)
            else:  # Or
                return any(self._evaluate_ast_node(value, facts) for value in node.values)
        
        elif isinstance(node, ast.UnaryOp):
            operand = self._evaluate_ast_node(node.operand, facts)
            if isinstance(node.op, ast.Not):
                return not operand
            elif isinstance(node.op, ast.UAdd):
                return +operand
            elif isinstance(node.op, ast.USub):
                return -operand
        
        elif isinstance(node, ast.Compare):
            return self._evaluate_compare(node, facts)
        
        elif isinstance(node, ast.BinOp):
            return self._evaluate_bin_op(node, facts)
        
        elif isinstance(node, ast.Call):
            return self._evaluate_call(node, facts)
        
        elif isinstance(node, ast.List):
            return [self._evaluate_ast_node(elem, facts) for elem in node.elts]
        
        # Legacy Python < 3.8 support
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.NameConstant):
            return node.value
        
        else:
            raise EvaluationError(f"Unsupported AST node type: {type(node)}")
    
    def _evaluate_compare(self, node: ast.Compare, facts: Dict[str, Any]) -> bool:
        """Evaluate comparison."""
        left = self._evaluate_ast_node(node.left, facts)
        
        for op, comparator in zip(node.ops, node.comparators):
            right = self._evaluate_ast_node(comparator, facts)
            
            try:
                if isinstance(op, ast.Eq):
                    result = left == right
                elif isinstance(op, ast.NotEq):
                    result = left != right
                elif isinstance(op, ast.Lt):
                    result = left < right
                elif isinstance(op, ast.LtE):
                    result = left <= right
                elif isinstance(op, ast.Gt):
                    result = left > right
                elif isinstance(op, ast.GtE):
                    result = left >= right
                elif isinstance(op, ast.In):
                    result = left in right if right is not None else False
                elif isinstance(op, ast.NotIn):
                    result = left not in right if right is not None else True
                elif isinstance(op, ast.Is):
                    result = left is right
                elif isinstance(op, ast.IsNot):
                    result = left is not right
                else:
                    raise EvaluationError(f"Unsupported comparison operator: {type(op)}")
                
                if not result:
                    return False
                    
            except (TypeError, ValueError):
                return False
            
            left = right  # For chained comparisons
        
        return True
    
    def _evaluate_bin_op(self, node: ast.BinOp, facts: Dict[str, Any]) -> Any:
        """Evaluate binary operation."""
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
            elif isinstance(node.op, ast.Mod):
                return left % right if right != 0 else 0
            elif isinstance(node.op, ast.Pow):
                return left ** right
            else:
                raise EvaluationError(f"Unsupported binary operator: {type(node.op)}")
        
        except (TypeError, ValueError, ZeroDivisionError):
            return None
    
    def _evaluate_call(self, node: ast.Call, facts: Dict[str, Any]) -> Any:
        """Evaluate function call."""
        func_name = node.func.id if isinstance(node.func, ast.Name) else str(node.func)
        
        if func_name not in self._functions:
            raise EvaluationError(f"Unknown function: {func_name}")
        
        # Evaluate arguments
        args = [self._evaluate_ast_node(arg, facts) for arg in node.args]
        
        try:
            return self._functions[func_name](*args)
        except Exception as e:
            raise EvaluationError(f"Function '{func_name}' failed: {e}") from e
    
    def _extract_names_from_ast(self, node: ast.AST, fields: Set[str]) -> None:
        """Extract field names from AST recursively."""
        if isinstance(node, ast.Name):
            fields.add(node.id)
        else:
            # Recursively visit child nodes
            for child in ast.iter_child_nodes(node):
                self._extract_names_from_ast(child, fields)
    
    def _extract_fields_regex(self, expression: str) -> Set[str]:
        """Fallback field extraction using regex."""
        fields = set()
        for match in FIELD_PATTERN.finditer(expression):
            field_name = match.group(1)
            if field_name not in RESERVED_WORDS:
                fields.add(field_name)
        return fields


# Factory function
def create_evaluator() -> SimpleConditionEvaluator:
    """Create evaluator instance."""
    return SimpleConditionEvaluator() 