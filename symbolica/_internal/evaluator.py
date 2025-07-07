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
from typing import Dict, Any, Set, Union, List, TYPE_CHECKING
from functools import lru_cache

# Import only what we need to avoid circular imports
from ..core.interfaces import ConditionEvaluator
from ..core.exceptions import EvaluationError

if TYPE_CHECKING:
    from ..core.models import ExecutionContext


# Pre-compiled patterns for performance
FIELD_PATTERN = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b')
RESERVED_WORDS = frozenset({
    'True', 'False', 'None', 'and', 'or', 'not', 'in', 'is',
    'len', 'sum', 'startswith', 'endswith', 'contains', 'abs'
})


class ASTEvaluator(ConditionEvaluator):
    """
    Simple, fast AST-based condition evaluator.
    
    Safely evaluates Python-like expressions against execution context.
    """
    
    def __init__(self):
        # Simple expression cache for performance
        self._cache: Dict[str, Any] = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def evaluate(self, condition_expr: str, context: 'ExecutionContext') -> bool:
        """Evaluate condition expression against context."""
        try:
            # Parse expression into AST
            tree = ast.parse(condition_expr.strip(), mode='eval')
            
            # Evaluate the AST
            result = self._eval_ast_node(tree.body, context)
            return bool(result)
            
        except Exception as e:
            raise EvaluationError(f"Evaluation error: {e}")
    
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