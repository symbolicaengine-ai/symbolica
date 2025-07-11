"""
Execution Path Evaluator
========================

Wrapper around CoreEvaluator that adds detailed execution path tracking.
Extracted from evaluator.py to follow Single Responsibility Principle.
"""

import ast
import time
from typing import Any, TYPE_CHECKING
from .core_evaluator import CoreEvaluator
from .execution_path import ExecutionPathBuilder, ExecutionPath, OperationType
from ...core.exceptions import EvaluationError, FunctionError, ValidationError

if TYPE_CHECKING:
    from ...core.models import ExecutionContext


class ExecutionPathEvaluator:
    """Evaluator that wraps CoreEvaluator and adds execution path tracking."""
    
    def __init__(self):
        """Initialize execution path evaluator with core evaluator."""
        self._core = CoreEvaluator()
    
    def register_function(self, name: str, func: Any) -> None:
        """Register a custom function."""
        self._core.register_function(name, func)
    
    def unregister_function(self, name: str) -> None:
        """Remove a custom function."""
        self._core.unregister_function(name)
    
    def evaluate_with_execution_path(self, condition_expr: str, context: 'ExecutionContext') -> ExecutionPath:
        """Evaluate condition and return detailed execution path."""
        start_time = time.perf_counter()
        
        try:
            tree = ast.parse(condition_expr.strip(), mode='eval')
            
            # Create execution path builder
            builder = ExecutionPathBuilder(condition_expr)
            
            # Evaluate with execution path tracking
            result = self._eval_node_with_path(tree.body, context, builder)
            
            # Calculate total execution time
            total_time_ms = (time.perf_counter() - start_time) * 1000
            
            # Finalize execution path
            return builder.finalize(bool(result), total_time_ms)
            
        except (EvaluationError, FunctionError, ValidationError):
            # Re-raise our custom exceptions with additional context
            raise
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
    
    def _eval_node_with_path(self, node, context: 'ExecutionContext', builder: ExecutionPathBuilder) -> Any:
        """Evaluate AST node and build execution path."""
        # Dispatch to specialized handlers with path tracking
        node_handlers = {
            ast.BoolOp: self._eval_bool_op_with_path,
            ast.Compare: self._eval_compare_with_path,
            ast.UnaryOp: self._eval_unary_op_with_path,
            ast.BinOp: self._eval_bin_op_with_path,
            ast.Call: self._eval_call_with_path,
            ast.Name: self._eval_name_with_path,
            ast.Constant: self._eval_constant_with_path,
            ast.List: self._eval_list_with_path,
            ast.Subscript: self._eval_subscript_with_path
        }
        
        handler = node_handlers.get(type(node))
        if handler:
            return handler(node, context, builder)
        
        raise EvaluationError(f"Unsupported AST node: {type(node).__name__}")
    
    def _eval_bool_op_with_path(self, node: ast.BoolOp, context: 'ExecutionContext', builder: ExecutionPathBuilder) -> Any:
        """Handle boolean operations with execution path tracking."""
        step_start = time.perf_counter()
        
        if isinstance(node.op, ast.And):
            step_id = builder.start_operation(OperationType.BOOLEAN_AND, "and")
            result = True
            evaluated_values = []
            
            for value_node in node.values:
                val = self._eval_node_with_path(value_node, context, builder)
                evaluated_values.append(val)
                if not val:
                    result = False
                    break  # Short circuit for AND
        else:  # OR
            step_id = builder.start_operation(OperationType.BOOLEAN_OR, "or")
            result = False
            evaluated_values = []
            
            for value_node in node.values:
                val = self._eval_node_with_path(value_node, context, builder)
                evaluated_values.append(val)
                if val:
                    result = True
                    break  # Short circuit for OR
        
        step_time = (time.perf_counter() - step_start) * 1000
        builder.finish_operation(step_id, result, {
            'operator': 'and' if isinstance(node.op, ast.And) else 'or',
            'operand_values': evaluated_values,
            'short_circuited': len(evaluated_values) < len(node.values)
        }, step_time)
        
        return result
    
    def _eval_compare_with_path(self, node: ast.Compare, context: 'ExecutionContext', builder: ExecutionPathBuilder) -> Any:
        """Handle comparison operations with execution path tracking."""
        step_start = time.perf_counter()
        step_id = builder.start_operation(OperationType.COMPARISON, "comparison")
        
        left = self._eval_node_with_path(node.left, context, builder)
        
        for op, comparator in zip(node.ops, node.comparators):
            right = self._eval_node_with_path(comparator, context, builder)
            
            result = self._compare(left, op, right)
            if not result:
                break
            left = right
        
        step_time = (time.perf_counter() - step_start) * 1000
        builder.finish_operation(step_id, result, {
            'comparison_type': type(node.ops[0]).__name__ if node.ops else 'unknown',
            'left_value': left,
            'right_value': right if 'right' in locals() else None
        }, step_time)
        
        return result
    
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
    
    def _eval_call_with_path(self, node: ast.Call, context: 'ExecutionContext', builder: ExecutionPathBuilder) -> Any:
        """Handle function calls with execution path tracking."""
        if not isinstance(node.func, ast.Name):
            raise EvaluationError("Only simple function calls are supported")
        
        func_name = node.func.id
        step_start = time.perf_counter()
        
        # Start tracking function call
        step_id = builder.start_operation(OperationType.FUNCTION_CALL, func_name)
        
        # Evaluate arguments
        args = []
        for arg in node.args:
            val = self._eval_node_with_path(arg, context, builder)
            args.append(val)
        
        # Execute function
        try:
            if func_name in self._core._builtin_functions:
                result = self._core._builtin_functions[func_name](args)
                function_type = "builtin"
                error = None
            elif func_name in self._core._custom_functions:
                result = self._core._custom_functions[func_name](*args)
                function_type = "custom"
                error = None
            else:
                raise EvaluationError(f"Unknown function: {func_name}")
        except Exception as e:
            result = None
            function_type = "unknown"
            error = str(e)
            if func_name in self._core._custom_functions:
                raise FunctionError(
                    f"Error in custom function: {str(e)}", 
                    function_name=func_name,
                    args=args,
                    original_error=e
                )
            else:
                raise EvaluationError(f"Function {func_name} failed: {str(e)}")
        
        step_time = (time.perf_counter() - step_start) * 1000
        builder.finish_operation(step_id, result, {
            'function_name': func_name,
            'function_type': function_type,
            'arguments': args,
            'error': error
        }, step_time)
        
        return result
    
    def _eval_name_with_path(self, node: ast.Name, context: 'ExecutionContext', builder: ExecutionPathBuilder) -> Any:
        """Handle name references with execution path tracking."""
        name = node.id
        
        # Handle boolean and null literals
        if name in ('True', 'False', 'None', 'true', 'false', 'null'):
            literal_map = {
                'True': True, 'true': True,
                'False': False, 'false': False, 
                'None': None, 'null': None
            }
            return literal_map[name]
        else:
            # Field access
            value = context.get_fact(name, None)
            is_missing = name not in context.enriched_facts
            
            # Record field access in builder
            builder.add_field_access(name, value, is_missing)
            
            return value
    
    def _eval_constant_with_path(self, node: ast.Constant, context: 'ExecutionContext', builder: ExecutionPathBuilder) -> Any:
        """Handle constant values with execution path tracking."""
        return node.value
    
    def _eval_unary_op_with_path(self, node: ast.UnaryOp, context: 'ExecutionContext', builder: ExecutionPathBuilder) -> Any:
        """Handle unary operations with execution path tracking."""
        step_start = time.perf_counter()
        step_id = builder.start_operation(OperationType.BOOLEAN_NOT, "unary_op")
        
        val = self._eval_node_with_path(node.operand, context, builder)
        
        if isinstance(node.op, ast.Not):
            result = not val
            operator = "not"
        elif isinstance(node.op, ast.UAdd):
            result = +val
            operator = "+"
        elif isinstance(node.op, ast.USub):
            result = -val
            operator = "-"
        else:
            raise EvaluationError(f"Unsupported unary operator: {type(node.op).__name__}")
        
        step_time = (time.perf_counter() - step_start) * 1000
        builder.finish_operation(step_id, result, {
            'operator': operator,
            'operand_value': val
        }, step_time)
        
        return result
    
    def _eval_bin_op_with_path(self, node: ast.BinOp, context: 'ExecutionContext', builder: ExecutionPathBuilder) -> Any:
        """Handle binary operations with execution path tracking."""
        left = self._eval_node_with_path(node.left, context, builder)
        right = self._eval_node_with_path(node.right, context, builder)
        
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
            raise EvaluationError(f"Type error: {e}")
        except ZeroDivisionError:
            raise EvaluationError("Division by zero")
        
        return result
    
    def _eval_list_with_path(self, node: ast.List, context: 'ExecutionContext', builder: ExecutionPathBuilder) -> Any:
        """Handle list literals with execution path tracking."""
        result = []
        for item in node.elts:
            val = self._eval_node_with_path(item, context, builder)
            result.append(val)
        return result
    
    def _eval_subscript_with_path(self, node: ast.Subscript, context: 'ExecutionContext', builder: ExecutionPathBuilder) -> Any:
        """Handle subscript operations with execution path tracking."""
        value = self._eval_node_with_path(node.value, context, builder)
        slice_val = self._eval_node_with_path(node.slice, context, builder)
        
        try:
            result = value[slice_val]
        except (IndexError, KeyError, TypeError) as e:
            raise EvaluationError(f"Subscript error: {e}")
        
        return result 