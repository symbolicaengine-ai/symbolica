"""
Field Extractor
===============

Utility for extracting field names from condition expressions.
Extracted from evaluator.py to follow Single Responsibility Principle.
"""

import ast
import re
from typing import Set
from ...core.exceptions import EvaluationError


class FieldExtractor:
    """Utility for extracting field names from condition expressions."""
    
    def __init__(self):
        """Initialize field extractor."""
        self._function_names: Set[str] = set()
    
    def update_function_names(self, function_names: Set[str]) -> None:
        """Update the set of known function names."""
        self._function_names = function_names.copy()
    
    def extract_fields_from_condition(self, condition_expr: str) -> Set[str]:
        """Extract field names from condition expression.
        
        Uses AST parsing to accurately identify field names,
        excluding function names and Python literals.
        
        Args:
            condition_expr: Condition expression string
            
        Returns:
            Set of field names found in the expression
        """
        if not condition_expr or not condition_expr.strip():
            return set()
        
        try:
            tree = ast.parse(condition_expr.strip(), mode='eval')
            return self._extract_from_ast(tree.body)
        except SyntaxError:
            # Fallback to regex-based extraction for malformed expressions
            return self._extract_with_regex_fallback(condition_expr)
    
    def _extract_from_ast(self, node) -> Set[str]:
        """Extract field names from AST node."""
        fields = set()
        
        # Handle different node types
        if isinstance(node, ast.Name):
            # Name reference - could be field or literal
            name = node.id
            if self._is_likely_field(name):
                fields.add(name)
        
        elif isinstance(node, ast.Call):
            # Function call - extract from arguments only
            if isinstance(node.func, ast.Name):
                # Don't include function name as field
                pass
            # Extract from arguments
            for arg in node.args:
                fields.update(self._extract_from_ast(arg))
        
        elif isinstance(node, ast.Compare):
            # Comparison - extract from left and comparators
            fields.update(self._extract_from_ast(node.left))
            for comparator in node.comparators:
                fields.update(self._extract_from_ast(comparator))
        
        elif isinstance(node, ast.BoolOp):
            # Boolean operation - extract from all values
            for value in node.values:
                fields.update(self._extract_from_ast(value))
        
        elif isinstance(node, ast.UnaryOp):
            # Unary operation - extract from operand
            fields.update(self._extract_from_ast(node.operand))
        
        elif isinstance(node, ast.BinOp):
            # Binary operation - extract from both sides
            fields.update(self._extract_from_ast(node.left))
            fields.update(self._extract_from_ast(node.right))
        
        elif isinstance(node, ast.Subscript):
            # Subscript operation - extract from value and slice
            fields.update(self._extract_from_ast(node.value))
            fields.update(self._extract_from_ast(node.slice))
        
        elif isinstance(node, ast.List):
            # List literal - extract from elements
            for elt in node.elts:
                fields.update(self._extract_from_ast(elt))
        
        elif isinstance(node, ast.Constant):
            # Constant value - no fields
            pass
        
        else:
            # Unknown node type - no fields
            pass
        
        return fields
    
    def _is_likely_field(self, name: str) -> bool:
        """Check if a name is likely a field reference."""
        # Exclude Python literals
        if name in ('True', 'False', 'None', 'true', 'false', 'null'):
            return False
        
        # Exclude known function names
        if name in self._function_names:
            return False
        
        # Include anything else that looks like an identifier
        return name.isidentifier()
    
    def _extract_with_regex_fallback(self, condition_expr: str) -> Set[str]:
        """Fallback field extraction using regex.
        
        Used when AST parsing fails due to syntax errors.
        Less accurate but provides some capability.
        """
        fields = set()
        
        # Find potential field names (simple word patterns)
        # This is a heuristic approach
        potential_fields = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', condition_expr)
        
        for field in potential_fields:
            if self._is_likely_field(field):
                fields.add(field)
        
        return fields 