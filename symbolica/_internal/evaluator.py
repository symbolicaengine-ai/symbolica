"""
AST-Based Expression Evaluator
==============================

Fast AST-based expression evaluation for deterministic AI agent reasoning.

Features:
- Python-like expression syntax
- Safe AST evaluation (no eval() vulnerabilities)
- Simple caching for performance
- Field extraction for DAG dependency analysis
- Detailed tracing for AI explainability
"""

import ast
import re
import time
from typing import Dict, Any, Set, Union, List, TYPE_CHECKING
from functools import lru_cache

# Import only what we need to avoid circular imports
from ..core.interfaces import ConditionEvaluator
from ..core.exceptions import EvaluationError

if TYPE_CHECKING:
    from ..core.models import ExecutionContext, FieldAccess, ConditionTrace


# Pre-compiled patterns for performance
FIELD_PATTERN = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b')
RESERVED_WORDS = frozenset({
    'True', 'False', 'None', 'and', 'or', 'not', 'in', 'is',
    'len', 'sum', 'startswith', 'endswith', 'contains', 'abs'
})


class TracingNameCollector(ast.NodeVisitor):
    """AST visitor that collects field names accessed during evaluation."""
    
    def __init__(self, context: 'ExecutionContext'):
        self.context = context
        self.field_accesses: List['FieldAccess'] = []
        
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id not in RESERVED_WORDS:
            # Import here to avoid circular imports
            from ..core.models import FieldAccess
            
            # This is a field access
            value = self.context.get_fact(node.id)
            field_access = FieldAccess(
                field_name=node.id,
                value=value,
                access_type='read',
                rule_id=self.context.current_rule_id
            )
            self.field_accesses.append(field_access)
        self.generic_visit(node)


class ASTEvaluator(ConditionEvaluator):
    """
    High-performance AST-based condition evaluator with detailed tracing.
    
    Safely evaluates Python-like expressions against execution context
    while capturing detailed trace information for AI explainability.
    """
    
    def __init__(self):
        # Simple expression cache for performance
        self._cache: Dict[str, Any] = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def evaluate(self, condition_expr: str, context: 'ExecutionContext') -> bool:
        """Evaluate condition expression against context."""
        result, _ = self.evaluate_with_trace(condition_expr, context)
        return result
    
    def evaluate_with_trace(self, condition_expr: str, context: 'ExecutionContext') -> tuple[bool, 'ConditionTrace']:
        """Evaluate condition expression and return detailed trace."""
        # Import here to avoid circular imports
        from ..core.models import ConditionTrace
        
        start_time = time.perf_counter_ns()
        field_accesses = []
        error_msg = None
        result = False
        
        try:
            # Parse expression into AST
            tree = ast.parse(condition_expr.strip(), mode='eval')
            
            # Collect field accesses
            name_collector = TracingNameCollector(context)
            name_collector.visit(tree)
            field_accesses = name_collector.field_accesses
            
            # Evaluate the AST
            result = self._eval_ast_node(tree.body, context)
            
        except Exception as e:
            error_msg = str(e)
            result = False
        
        evaluation_time = time.perf_counter_ns() - start_time
        
        condition_trace = ConditionTrace(
            expression=condition_expr,
            result=result,
            evaluation_time_ns=evaluation_time,
            field_accesses=field_accesses,
            error=error_msg
        )
        
        return result, condition_trace
    
    def _eval_ast_node(self, node, context: 'ExecutionContext') -> Any:
        """Recursively evaluate AST nodes."""
        if isinstance(node, ast.BoolOp):
            return self._eval_bool_op(node, context)
        elif isinstance(node, ast.Compare):
            return self._eval_compare(node, context)
        elif isinstance(node, ast.UnaryOp):
            return self._eval_unary_op(node, context)
        elif isinstance(node, ast.BinOp):
            return self._eval_bin_op(node, context)
        elif isinstance(node, ast.Call):
            return self._eval_call(node, context)
        elif isinstance(node, ast.Name):
            return self._eval_name(node, context)
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.List):
            return [self._eval_ast_node(item, context) for item in node.elts]
        elif isinstance(node, ast.Subscript):
            return self._eval_subscript(node, context)
        else:
            raise EvaluationError(f"Unsupported AST node type: {type(node).__name__}")
    
    def _eval_bool_op(self, node, context: 'ExecutionContext') -> bool:
        """Evaluate boolean operations (and, or)."""
        if isinstance(node.op, ast.And):
            return all(self._eval_ast_node(value, context) for value in node.values)
        elif isinstance(node.op, ast.Or):
            return any(self._eval_ast_node(value, context) for value in node.values)
        else:
            raise EvaluationError(f"Unsupported boolean operator: {type(node.op).__name__}")
    
    def _eval_compare(self, node, context: 'ExecutionContext') -> bool:
        """Evaluate comparison operations."""
        left = self._eval_ast_node(node.left, context)
        
        for op, comparator in zip(node.ops, node.comparators):
            right = self._eval_ast_node(comparator, context)
            
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
                result = left in right
            elif isinstance(op, ast.NotIn):
                result = left not in right
            elif isinstance(op, ast.Is):
                result = left is right
            elif isinstance(op, ast.IsNot):
                result = left is not right
            else:
                raise EvaluationError(f"Unsupported comparison operator: {type(op).__name__}")
            
            if not result:
                return False
            left = right  # For chained comparisons
        
        return True
    
    def _eval_unary_op(self, node, context: 'ExecutionContext') -> Any:
        """Evaluate unary operations."""
        operand = self._eval_ast_node(node.operand, context)
        
        if isinstance(node.op, ast.Not):
            return not operand
        elif isinstance(node.op, ast.UAdd):
            return +operand
        elif isinstance(node.op, ast.USub):
            return -operand
        else:
            raise EvaluationError(f"Unsupported unary operator: {type(node.op).__name__}")
    
    def _eval_bin_op(self, node, context: 'ExecutionContext') -> Any:
        """Evaluate binary operations."""
        left = self._eval_ast_node(node.left, context)
        right = self._eval_ast_node(node.right, context)
        
        if isinstance(node.op, ast.Add):
            return left + right
        elif isinstance(node.op, ast.Sub):
            return left - right
        elif isinstance(node.op, ast.Mult):
            return left * right
        elif isinstance(node.op, ast.Div):
            if right == 0:
                raise EvaluationError("Division by zero")
            return left / right
        elif isinstance(node.op, ast.Mod):
            return left % right
        elif isinstance(node.op, ast.Pow):
            return left ** right
        else:
            raise EvaluationError(f"Unsupported binary operator: {type(node.op).__name__}")
    
    def _eval_call(self, node, context: 'ExecutionContext') -> Any:
        """Evaluate function calls."""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            args = [self._eval_ast_node(arg, context) for arg in node.args]
            
            # Built-in functions
            if func_name == 'len':
                return len(args[0]) if args else 0
            elif func_name == 'sum':
                return sum(args[0]) if args and hasattr(args[0], '__iter__') else 0
            elif func_name == 'abs':
                return abs(args[0]) if args else 0
            elif func_name == 'startswith':
                return args[0].startswith(args[1]) if len(args) >= 2 else False
            elif func_name == 'endswith':
                return args[0].endswith(args[1]) if len(args) >= 2 else False
            elif func_name == 'contains':
                return args[1] in args[0] if len(args) >= 2 else False
            else:
                raise EvaluationError(f"Unknown function: {func_name}")
        else:
            raise EvaluationError("Complex function calls not supported")
    
    def _eval_name(self, node, context: 'ExecutionContext') -> Any:
        """Evaluate name lookups (variables/fields)."""
        name = node.id
        
        # Reserved constants
        if name == 'True':
            return True
        elif name == 'False':
            return False
        elif name == 'None':
            return None
        else:
            # Field lookup
            if name in context.enriched_facts:
                return context.get_fact(name)
            else:
                raise EvaluationError(f"Unknown field: {name}")
    
    def _eval_subscript(self, node, context: 'ExecutionContext') -> Any:
        """Evaluate subscript operations (list[index], dict[key])."""
        value = self._eval_ast_node(node.value, context)
        slice_value = self._eval_ast_node(node.slice, context)
        return value[slice_value]
    
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
            # Fallback to regex
            matches = FIELD_PATTERN.findall(condition_expr)
            return {match for match in matches if match not in RESERVED_WORDS}


def create_evaluator() -> ASTEvaluator:
    """Factory function to create AST evaluator."""
    return ASTEvaluator() 