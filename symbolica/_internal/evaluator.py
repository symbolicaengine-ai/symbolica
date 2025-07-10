"""
AST-Based Expression Evaluator
==============================

Simple AST-based expression evaluation with built-in tracing for AI agents.
"""

import ast
import re
from typing import Dict, Any, Set, Tuple, TYPE_CHECKING, Callable
from functools import lru_cache
from dataclasses import dataclass

from ..core.interfaces import ConditionEvaluator
from ..core.exceptions import EvaluationError

if TYPE_CHECKING:
    from ..core.models import ExecutionContext


@dataclass
class ConditionTrace:
    """Simple trace for condition evaluation."""
    expression: str
    result: bool
    field_values: Dict[str, Any]
    
    def explain(self) -> str:
        """Generate human-readable explanation with field values."""
        expr = self.expression
        for field, value in self.field_values.items():
            if field in expr:
                expr = expr.replace(field, f"{field}({value})")
        
        # Add contextual prefixes for better readability
        if ' or ' in expr.lower():
            return f"Condition true because: {expr}"
        elif ' and ' in expr.lower():
            return f"Condition true: {expr}"
        else:
            return expr


# Pre-compiled patterns
FIELD_PATTERN = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b')
RESERVED_WORDS = frozenset({
    'True', 'False', 'None', 'and', 'or', 'not', 'in', 'is',
    'true', 'false', 'null',  # Common lowercase boolean/null literals
    'len', 'sum', 'startswith', 'endswith', 'contains', 'abs'
})


class ASTEvaluator(ConditionEvaluator):
    """Simple AST-based condition evaluator with built-in tracing."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._custom_functions: Dict[str, Callable] = {}
        self._builtin_functions = self._setup_builtin_functions()
    
    def _setup_builtin_functions(self) -> Dict[str, Callable]:
        """Setup built-in function registry - cleaner than if-elif chain."""
        def safe_len(args):
            return len(args[0]) if args else 0
        
        def safe_sum(args):
            return sum(args[0]) if args and hasattr(args[0], '__iter__') else 0
        
        def safe_abs(args):
            return abs(args[0]) if args else 0
        
        def safe_startswith(args):
            return args[0].startswith(args[1]) if len(args) >= 2 else False
        
        def safe_endswith(args):
            return args[0].endswith(args[1]) if len(args) >= 2 else False
        
        def safe_contains(args):
            return args[1] in args[0] if len(args) >= 2 else False
        
        return {
            'len': safe_len,
            'sum': safe_sum,
            'abs': safe_abs,
            'startswith': safe_startswith,
            'endswith': safe_endswith,
            'contains': safe_contains
        }
    
    def register_function(self, name: str, func: Callable) -> None:
        """Register a custom function."""
        if not callable(func):
            raise ValueError(f"Function {name} must be callable")
        if not name.isidentifier():
            raise ValueError(f"Function name {name} must be a valid identifier")
        if name in RESERVED_WORDS:
            raise ValueError(f"Function name {name} is reserved")
        
        self._custom_functions[name] = func
    
    def unregister_function(self, name: str) -> None:
        """Remove a registered custom function."""
        self._custom_functions.pop(name, None)
    
    def list_functions(self) -> Dict[str, str]:
        """List all available functions."""
        # Use registry instead of hardcoded descriptions
        builtin_descriptions = {
            'len': 'Get length of sequence',
            'sum': 'Sum elements of sequence', 
            'abs': 'Absolute value',
            'startswith': 'Check if string starts with substring',
            'endswith': 'Check if string ends with substring',
            'contains': 'Check if sequence contains element'
        }
        built_in = {name: builtin_descriptions.get(name, f'Built-in function: {name}') 
                   for name in self._builtin_functions.keys()}
        custom = {name: f'Custom function: {func.__name__ if hasattr(func, "__name__") else "lambda"}' 
                 for name, func in self._custom_functions.items()}
        return {**built_in, **custom}
    
    def evaluate(self, condition_expr: str, context: 'ExecutionContext') -> bool:
        """Evaluate condition expression."""
        return self.evaluate_with_trace(condition_expr, context).result
    
    def evaluate_with_trace(self, condition_expr: str, context: 'ExecutionContext') -> ConditionTrace:
        """Evaluate condition and return trace information."""
        try:
            tree = ast.parse(condition_expr.strip(), mode='eval')
            result, field_values = self._eval_node(tree.body, context)
            return ConditionTrace(condition_expr, bool(result), field_values)
        except Exception as e:
            raise EvaluationError(f"Evaluation error: {e}")
    
    def _eval_node(self, node, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Evaluate AST node and collect field values."""
        # Dispatch to specialized handlers - cleaner than giant if-elif chain
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
            return result, field_values
        elif isinstance(node.op, ast.Or):
            result = False
            for value_node in node.values:
                val, fields = self._eval_node(value_node, context)
                field_values.update(fields)
                if val:
                    result = True
            return result, field_values
    
    def _eval_compare(self, node: ast.Compare, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Handle comparison operations (==, !=, <, >, etc.)."""
        field_values = {}
        left, left_fields = self._eval_node(node.left, context)
        field_values.update(left_fields)
        
        for op, comparator in zip(node.ops, node.comparators):
            right, right_fields = self._eval_node(comparator, context)
            field_values.update(right_fields)
            
            result = self._compare(left, op, right)
            if not result:
                return False, field_values
            left = right
        return True, field_values
    
    def _eval_unary_op(self, node: ast.UnaryOp, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Handle unary operations (not, +, -)."""
        if isinstance(node.op, ast.Not):
            val, fields = self._eval_node(node.operand, context)
            return not val, fields
        elif isinstance(node.op, ast.UAdd):
            val, fields = self._eval_node(node.operand, context)
            return +val, fields
        elif isinstance(node.op, ast.USub):
            val, fields = self._eval_node(node.operand, context)
            return -val, fields
    
    def _eval_bin_op(self, node: ast.BinOp, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Handle binary operations (+, -, *, /, etc.)."""
        left, left_fields = self._eval_node(node.left, context)
        right, right_fields = self._eval_node(node.right, context)
        field_values = {**left_fields, **right_fields}
        
        try:
            if isinstance(node.op, ast.Add):
                return left + right, field_values
            elif isinstance(node.op, ast.Sub):
                return left - right, field_values
            elif isinstance(node.op, ast.Mult):
                return left * right, field_values
            elif isinstance(node.op, ast.Div):
                if right == 0:
                    raise EvaluationError("Division by zero")
                return left / right, field_values
            elif isinstance(node.op, ast.Mod):
                return left % right, field_values
            elif isinstance(node.op, ast.Pow):
                return left ** right, field_values
        except TypeError as e:
            raise EvaluationError(f"Type error: {e}")
        except ZeroDivisionError:
            raise EvaluationError("Division by zero")
    
    def _eval_call(self, node: ast.Call, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Handle function calls."""
        if not isinstance(node.func, ast.Name):
            raise EvaluationError("Only simple function calls are supported")
        
        func_name = node.func.id
        field_values = {}
        args = []
        
        # Evaluate arguments
        for arg in node.args:
            val, fields = self._eval_node(arg, context)
            field_values.update(fields)
            args.append(val)
        
        # Try built-in functions first
        if func_name in self._builtin_functions:
            result = self._builtin_functions[func_name](args)
            return result, field_values
        
        # Try custom functions
        elif func_name in self._custom_functions:
            try:
                result = self._custom_functions[func_name](*args)
                return result, field_values
            except (TypeError, ValueError, ZeroDivisionError) as e:
                raise EvaluationError(f"Error in custom function {func_name}: {e}")
            except Exception as e:
                raise EvaluationError(f"Unexpected error in custom function {func_name}: {e}")
        
        else:
            raise EvaluationError(f"Unknown function: {func_name}")
    
    def _eval_name(self, node: ast.Name, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Handle name references (variables, literals)."""
        field_values = {}
        name = node.id
        
        # Handle boolean and null literals (both capitalized and lowercase)
        if name in ('True', 'False', 'None', 'true', 'false', 'null'):
            literal_map = {
                'True': True, 'true': True,
                'False': False, 'false': False, 
                'None': None, 'null': None
            }
            return literal_map[name], field_values
        else:
            # Get fact value, default to None for missing fields
            # This enables rule chaining where rules depend on facts set by other rules
            value = context.get_fact(name, None)
            field_values[name] = value
            return value, field_values
    
    def _eval_constant(self, node: ast.Constant, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Handle constant values."""
        return node.value, {}
    
    def _eval_list(self, node: ast.List, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Handle list literals."""
        field_values = {}
        result = []
        for item in node.elts:
            val, fields = self._eval_node(item, context)
            field_values.update(fields)
            result.append(val)
        return result, field_values
    
    def _eval_subscript(self, node: ast.Subscript, context: 'ExecutionContext') -> Tuple[Any, Dict[str, Any]]:
        """Handle subscript operations (list[index])."""
        value, value_fields = self._eval_node(node.value, context)
        slice_val, slice_fields = self._eval_node(node.slice, context)
        field_values = {**value_fields, **slice_fields}
        return value[slice_val], field_values
    
    def _compare(self, left: Any, op: ast.cmpop, right: Any) -> bool:
        """Compare two values."""
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
        return False
    
    def extract_fields(self, condition_expr: str) -> Set[str]:
        """Extract field names from condition expression."""
        try:
            tree = ast.parse(condition_expr.strip(), mode='eval')
            fields = set()
            
            # Create dynamic reserved words including all functions
            all_reserved = (RESERVED_WORDS | 
                          set(self._custom_functions.keys()) | 
                          set(self._builtin_functions.keys()))
            
            class FieldCollector(ast.NodeVisitor):
                def visit_Name(self, node):
                    if isinstance(node.ctx, ast.Load) and node.id not in all_reserved:
                        fields.add(node.id)
                        
                def visit_Call(self, node):
                    # Don't treat function names as fields
                    if isinstance(node.func, ast.Name):
                        # Visit arguments but not the function name
                        for arg in node.args:
                            self.visit(arg)
                    else:
                        self.generic_visit(node)
            
            FieldCollector().visit(tree)
            return fields
        except (SyntaxError, ValueError):
            # Fallback to regex if AST parsing fails
            matches = FIELD_PATTERN.findall(condition_expr)
            all_reserved = (RESERVED_WORDS | 
                          set(self._custom_functions.keys()) | 
                          set(self._builtin_functions.keys()))
            return {match for match in matches if match not in all_reserved}
        except Exception as e:
            # Handle unexpected errors
            raise EvaluationError(f"Error extracting fields from condition: {e}")


 