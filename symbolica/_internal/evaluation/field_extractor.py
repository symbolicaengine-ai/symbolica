"""
Field Extractor Utility
=======================

Utility for extracting field names from condition expressions.
Extracted from evaluator.py to follow Single Responsibility Principle.
"""

import ast
from typing import Set, List
from ...core.infrastructure.exceptions import EvaluationError


class FieldExtractor:
    """Utility for extracting field names from condition expressions."""
    
    def __init__(self, function_names: Set[str] = None):
        """Initialize field extractor with optional function names to exclude."""
        self._function_names = function_names or set()
    
    def update_function_names(self, function_names: Set[str]) -> None:
        """Update the set of function names to exclude from field extraction."""
        self._function_names = function_names
    
    def extract_fields_from_condition(self, condition_expr: str) -> Set[str]:
        """Extract field names from condition expression.
        
        Args:
            condition_expr: The condition expression to analyze
            
        Returns:
            Set of field names referenced in the condition
            
        Raises:
            EvaluationError: If the condition expression is invalid
        """
        try:
            tree = ast.parse(condition_expr.strip(), mode='eval')
            fields = set()
            self._extract_fields_from_node(tree.body, fields)
            return fields
        except SyntaxError as e:
            raise EvaluationError(f"Invalid syntax in condition: {e}")
        except Exception as e:
            raise EvaluationError(f"Error extracting fields from condition: {e}")
    
    def _extract_fields_from_node(self, node, fields: Set[str]) -> None:
        """Recursively extract field names from AST node."""
        if isinstance(node, ast.Name):
            # Variable reference - could be a field
            name = node.id
            
            # Skip boolean and null literals
            if name not in ('True', 'False', 'None', 'true', 'false', 'null'):
                # Skip function names
                if name not in self._function_names:
                    fields.add(name)
                    
        elif isinstance(node, ast.Call):
            # Function call - extract from arguments but not function name
            for arg in node.args:
                self._extract_fields_from_node(arg, fields)
                
        elif isinstance(node, ast.BoolOp):
            # Boolean operation (and, or)
            for value in node.values:
                self._extract_fields_from_node(value, fields)
                
        elif isinstance(node, ast.Compare):
            # Comparison operation
            self._extract_fields_from_node(node.left, fields)
            for comparator in node.comparators:
                self._extract_fields_from_node(comparator, fields)
                
        elif isinstance(node, ast.UnaryOp):
            # Unary operation (not, +, -)
            self._extract_fields_from_node(node.operand, fields)
            
        elif isinstance(node, ast.BinOp):
            # Binary operation (+, -, *, /, etc.)
            self._extract_fields_from_node(node.left, fields)
            self._extract_fields_from_node(node.right, fields)
            
        elif isinstance(node, ast.List):
            # List literal
            for item in node.elts:
                self._extract_fields_from_node(item, fields)
                
        elif isinstance(node, ast.Subscript):
            # Subscript operation (indexing)
            self._extract_fields_from_node(node.value, fields)
            self._extract_fields_from_node(node.slice, fields)
            
        elif isinstance(node, ast.Constant):
            # Constant value - no fields to extract
            pass
            
        else:
            # Other node types - try to recurse through child nodes
            for child in ast.iter_child_nodes(node):
                self._extract_fields_from_node(child, fields) 