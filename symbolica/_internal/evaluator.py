"""
AST-Based Expression Evaluator
==============================

Simple AST-based expression evaluation with built-in tracing for AI agents.
"""

import ast
import re
from typing import Dict, Any, Set, TYPE_CHECKING
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
    'len', 'sum', 'startswith', 'endswith', 'contains', 'abs'
})


class ASTEvaluator(ConditionEvaluator):
    """Simple AST-based condition evaluator with built-in tracing."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
    
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
    
    def _eval_node(self, node, context: 'ExecutionContext') -> tuple[Any, Dict[str, Any]]:
        """Evaluate AST node and collect field values."""
        field_values = {}
        
        if isinstance(node, ast.BoolOp):
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
                
        elif isinstance(node, ast.Compare):
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
            
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                val, fields = self._eval_node(node.operand, context)
                return not val, fields
            elif isinstance(node.op, ast.UAdd):
                val, fields = self._eval_node(node.operand, context)
                return +val, fields
            elif isinstance(node.op, ast.USub):
                val, fields = self._eval_node(node.operand, context)
                return -val, fields
                
        elif isinstance(node, ast.BinOp):
            left, left_fields = self._eval_node(node.left, context)
            right, right_fields = self._eval_node(node.right, context)
            field_values.update(left_fields)
            field_values.update(right_fields)
            
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
                
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                args = []
                for arg in node.args:
                    val, fields = self._eval_node(arg, context)
                    field_values.update(fields)
                    args.append(val)
                
                if func_name == 'len':
                    return len(args[0]) if args else 0, field_values
                elif func_name == 'sum':
                    return sum(args[0]) if args and hasattr(args[0], '__iter__') else 0, field_values
                elif func_name == 'abs':
                    return abs(args[0]) if args else 0, field_values
                elif func_name == 'startswith':
                    return args[0].startswith(args[1]) if len(args) >= 2 else False, field_values
                elif func_name == 'endswith':
                    return args[0].endswith(args[1]) if len(args) >= 2 else False, field_values
                elif func_name == 'contains':
                    return args[1] in args[0] if len(args) >= 2 else False, field_values
                else:
                    raise EvaluationError(f"Unknown function: {func_name}")
                    
        elif isinstance(node, ast.Name):
            name = node.id
            if name in ('True', 'False', 'None'):
                return {'True': True, 'False': False, 'None': None}[name], field_values
            else:
                if name in context.enriched_facts:
                    value = context.get_fact(name)
                    field_values[name] = value
                    return value, field_values
                else:
                    raise EvaluationError(f"Unknown field: {name}")
                    
        elif isinstance(node, ast.Constant):
            return node.value, field_values
            
        elif isinstance(node, ast.List):
            result = []
            for item in node.elts:
                val, fields = self._eval_node(item, context)
                field_values.update(fields)
                result.append(val)
            return result, field_values
            
        elif isinstance(node, ast.Subscript):
            value, value_fields = self._eval_node(node.value, context)
            slice_val, slice_fields = self._eval_node(node.slice, context)
            field_values.update(value_fields)
            field_values.update(slice_fields)
            return value[slice_val], field_values
            
        raise EvaluationError(f"Unsupported AST node: {type(node).__name__}")
    
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
    
    @lru_cache(maxsize=128)
    def extract_fields(self, condition_expr: str) -> Set[str]:
        """Extract field names from condition expression."""
        try:
            tree = ast.parse(condition_expr.strip(), mode='eval')
            fields = set()
            
            class FieldCollector(ast.NodeVisitor):
                def visit_Name(self, node):
                    if isinstance(node.ctx, ast.Load) and node.id not in RESERVED_WORDS:
                        fields.add(node.id)
            
            FieldCollector().visit(tree)
            return fields
        except:
            matches = FIELD_PATTERN.findall(condition_expr)
            return {match for match in matches if match not in RESERVED_WORDS}


 