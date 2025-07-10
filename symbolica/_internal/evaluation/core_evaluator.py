"""
Core AST Evaluator
==================

Lean evaluator focused solely on converting AST nodes to results.
No tracing, no execution paths - just pure evaluation logic.
Extracted from evaluator.py to follow Single Responsibility Principle.
"""

import ast
from typing import Any, Dict, Tuple, Callable, TYPE_CHECKING
from ...core.exceptions import EvaluationError, FunctionError
from .builtin_functions import get_builtin_functions

if TYPE_CHECKING:
    from ...core.models import ExecutionContext


class CoreEvaluator:
    """Core AST evaluator focused solely on evaluation logic."""
    
    def __init__(self):
        """Initialize core evaluator with built-in functions."""
        self._builtin_functions = get_builtin_functions()
        self._custom_functions: Dict[str, Callable] = {}
    
    def register_function(self, name: str, func: Callable) -> None:
        """Register a custom function."""
        self._custom_functions[name] = func
    
    def unregister_function(self, name: str) -> None:
        """Remove a custom function."""
        self._custom_functions.pop(name, None)
    
    def evaluate(self, condition_expr: str, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Evaluate condition expression and return result with field values."""
        try:
            tree = ast.parse(condition_expr.strip(), mode='eval')
            return self._eval_node(tree.body, context)
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
    
    def _eval_node(self, node, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Evaluate AST node and return result with field values."""
        # Dispatch to specialized handlers
        node_handlers = {
            ast.BoolOp: self._eval_bool_op,
            ast.Compare: self._eval_compare,
            ast.UnaryOp: self._eval_unary_op,
            ast.BinOp: self._eval_bin_op,
            ast.Call: self._eval_call,
            ast.Name: self._eval_name,
            ast.Constant: self._eval_constant,
            ast.List: self._eval_list,
            ast.Subscript: self._eval_subscript
        }
        
        handler = node_handlers.get(type(node))
        if handler:
            return handler(node, context)
        
        raise EvaluationError(f"Unsupported AST node: {type(node).__name__}")
    
    def _eval_bool_op(self, node: ast.BoolOp, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Handle boolean operations (and, or)."""
        field_values = {}
        
        if isinstance(node.op, ast.And):
            result = True
            for value_node in node.values:
                val, fields = self._eval_node(value_node, context)
                field_values.update(fields)
                if not val:
                    result = False
                    break  # Short circuit for AND
        else:  # OR
            result = False
            for value_node in node.values:
                val, fields = self._eval_node(value_node, context)
                field_values.update(fields)
                if val:
                    result = True
                    break  # Short circuit for OR
        
        return result, field_values
    
    def _eval_compare(self, node: ast.Compare, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Handle comparison operations."""
        field_values = {}
        left, left_fields = self._eval_node(node.left, context)
        field_values.update(left_fields)
        
        for op, comparator in zip(node.ops, node.comparators):
            right, right_fields = self._eval_node(comparator, context)
            field_values.update(right_fields)
            
            result = self._compare(left, op, right)
            if not result:
                break
            left = right
        
        return result, field_values
    
    def _compare(self, left: Any, op: ast.cmpop, right: Any) -> bool:
        """Perform comparison operation."""
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
                return left in right
            elif isinstance(op, ast.NotIn):
                return left not in right
            elif isinstance(op, ast.Is):
                return left is right
            elif isinstance(op, ast.IsNot):
                return left is not right
            else:
                raise EvaluationError(f"Unsupported comparison operator: {type(op).__name__}")
        except TypeError as e:
            raise EvaluationError(f"Type error in comparison: {e}")
    
    def _eval_unary_op(self, node: ast.UnaryOp, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Handle unary operations (not, +, -)."""
        val, field_values = self._eval_node(node.operand, context)
        
        if isinstance(node.op, ast.Not):
            result = not val
        elif isinstance(node.op, ast.UAdd):
            result = +val
        elif isinstance(node.op, ast.USub):
            result = -val
        else:
            raise EvaluationError(f"Unsupported unary operator: {type(node.op).__name__}")
        
        return result, field_values
    
    def _eval_bin_op(self, node: ast.BinOp, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Handle binary operations (+, -, *, /, etc.)."""
        left, left_fields = self._eval_node(node.left, context)
        right, right_fields = self._eval_node(node.right, context)
        
        field_values = {**left_fields, **right_fields}
        
        try:
            if isinstance(node.op, ast.Add):
                result = left + right
            elif isinstance(node.op, ast.Sub):
                result = left - right
            elif isinstance(node.op, ast.Mult):
                result = left * right
            elif isinstance(node.op, ast.Div):
                if right == 0:
                    raise EvaluationError("Division by zero")
                result = left / right
            elif isinstance(node.op, ast.Mod):
                result = left % right
            elif isinstance(node.op, ast.Pow):
                result = left ** right
            else:
                raise EvaluationError(f"Unsupported binary operator: {type(node.op).__name__}")
                
        except TypeError as e:
            raise EvaluationError(f"Type error in arithmetic: {e}")
        except ZeroDivisionError:
            raise EvaluationError("Division by zero")
        
        return result, field_values
    
    def _eval_call(self, node: ast.Call, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Handle function calls."""
        if not isinstance(node.func, ast.Name):
            raise EvaluationError("Only simple function calls are supported")
        
        func_name = node.func.id
        
        # Evaluate arguments
        args = []
        field_values = {}
        for arg in node.args:
            val, fields = self._eval_node(arg, context)
            args.append(val)
            field_values.update(fields)
        
        # Execute function
        try:
            if func_name in self._builtin_functions:
                result = self._builtin_functions[func_name](args)
            elif func_name in self._custom_functions:
                result = self._custom_functions[func_name](*args)
            else:
                raise EvaluationError(f"Unknown function: {func_name}")
        except Exception as e:
            if func_name in self._custom_functions:
                raise FunctionError(
                    f"Error in custom function: {str(e)}", 
                    function_name=func_name,
                    args=args,
                    original_error=e
                )
            else:
                raise EvaluationError(f"Function {func_name} failed: {str(e)}")
        
        return result, field_values
    
    def _eval_name(self, node: ast.Name, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Handle name references (variables, literals)."""
        name = node.id
        
        # Handle boolean and null literals
        if name in ('True', 'False', 'None', 'true', 'false', 'null'):
            literal_map = {
                'True': True, 'true': True,
                'False': False, 'false': False, 
                'None': None, 'null': None
            }
            return literal_map[name], {}
        else:
            # Field access
            value = context.get_fact(name, None)
            return value, {name: value}
    
    def _eval_constant(self, node: ast.Constant, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Handle constant values."""
        return node.value, {}
    
    def _eval_list(self, node: ast.List, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Handle list literals."""
        result = []
        field_values = {}
        
        for item in node.elts:
            val, fields = self._eval_node(item, context)
            result.append(val)
            field_values.update(fields)
        
        return result, field_values
    
    def _eval_subscript(self, node: ast.Subscript, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Handle subscript operations (indexing)."""
        value, value_fields = self._eval_node(node.value, context)
        slice_val, slice_fields = self._eval_node(node.slice, context)
        
        field_values = {**value_fields, **slice_fields}
        
        try:
            result = value[slice_val]
        except (IndexError, KeyError, TypeError) as e:
            raise EvaluationError(f"Subscript error: {e}")
        
        return result, field_values 