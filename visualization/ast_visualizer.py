"""
AST Visualizer for Rule Conditions
==================================

Visualizes how rule conditions are parsed into abstract syntax trees.
"""

import ast
import json
from typing import Dict, List, Any, Optional


class ASTVisualizer:
    """Visualizes the AST structure of rule conditions."""
    
    def __init__(self, rules: List[Any]):
        self.rules = rules
        self.ast_cache = {}
    
    def parse_condition(self, condition: str) -> Dict[str, Any]:
        """Parse a condition string into AST representation."""
        if condition in self.ast_cache:
            return self.ast_cache[condition]
        
        try:
            # Parse as Python expression
            tree = ast.parse(condition, mode='eval')
            ast_dict = self._ast_to_dict(tree.body)
            self.ast_cache[condition] = ast_dict
            return ast_dict
        except SyntaxError:
            # Handle simple comparison format like "age > 18"
            return self._parse_simple_condition(condition)
    
    def _ast_to_dict(self, node: ast.AST) -> Dict[str, Any]:
        """Convert AST node to dictionary representation."""
        result = {'type': node.__class__.__name__}
        
        if isinstance(node, ast.Compare):
            result['left'] = self._ast_to_dict(node.left)
            result['ops'] = [op.__class__.__name__ for op in node.ops]
            result['comparators'] = [self._ast_to_dict(comp) for comp in node.comparators]
        
        elif isinstance(node, ast.BoolOp):
            result['op'] = node.op.__class__.__name__
            result['values'] = [self._ast_to_dict(val) for val in node.values]
        
        elif isinstance(node, ast.UnaryOp):
            result['op'] = node.op.__class__.__name__
            result['operand'] = self._ast_to_dict(node.operand)
        
        elif isinstance(node, ast.Name):
            result['id'] = node.id
        
        elif isinstance(node, ast.Constant):
            result['value'] = node.value
        
        elif isinstance(node, ast.Attribute):
            result['value'] = self._ast_to_dict(node.value)
            result['attr'] = node.attr
        
        elif isinstance(node, ast.Subscript):
            result['value'] = self._ast_to_dict(node.value)
            result['slice'] = self._ast_to_dict(node.slice)
        
        return result
    
    def _parse_simple_condition(self, condition: str) -> Dict[str, Any]:
        """Parse simple conditions like 'age > 18'."""
        condition = condition.strip()
        
        # Handle basic comparisons
        for op in ['>=', '<=', '==', '!=', '>', '<']:
            if op in condition:
                left, right = condition.split(op, 1)
                return {
                    'type': 'Compare',
                    'left': {'type': 'Name', 'id': left.strip()},
                    'ops': [self._op_to_ast_name(op)],
                    'comparators': [{'type': 'Constant', 'value': self._parse_value(right.strip())}]
                }
        
        # Handle 'in' operations
        if ' in ' in condition:
            left, right = condition.split(' in ', 1)
            return {
                'type': 'Compare',
                'left': {'type': 'Name', 'id': left.strip()},
                'ops': ['In'],
                'comparators': [{'type': 'Constant', 'value': self._parse_value(right.strip())}]
            }
        
        # Default to simple name
        return {'type': 'Name', 'id': condition}
    
    def _op_to_ast_name(self, op: str) -> str:
        """Convert operator string to AST class name."""
        mapping = {
            '>': 'Gt', '<': 'Lt', '>=': 'GtE', '<=': 'LtE',
            '==': 'Eq', '!=': 'NotEq'
        }
        return mapping.get(op, 'Eq')
    
    def _parse_value(self, value: str) -> Any:
        """Parse string value to appropriate type."""
        value = value.strip()
        
        # Try to parse as number
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # Try to parse as boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Remove quotes if present
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        
        return value
    
    def get_ast_tree(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get AST tree for a specific rule."""
        for rule in self.rules:
            if rule.id == rule_id:
                return self.parse_condition(rule.condition)
        return None
    
    def get_all_asts(self) -> Dict[str, Dict[str, Any]]:
        """Get AST trees for all rules."""
        return {
            rule.id: self.parse_condition(rule.condition)
            for rule in self.rules
        }
    
    def to_text_tree(self, ast_dict: Dict[str, Any], indent: int = 0) -> str:
        """Convert AST dictionary to readable text tree."""
        spaces = "  " * indent
        node_type = ast_dict.get('type', 'Unknown')
        
        if node_type == 'Compare':
            left = self.to_text_tree(ast_dict['left'], indent + 1)
            ops = " ".join(ast_dict.get('ops', []))
            comparators = " ".join([
                self.to_text_tree(comp, 0) 
                for comp in ast_dict.get('comparators', [])
            ])
            return f"{spaces}Compare:\n{left}\n{spaces}  Ops: {ops}\n{spaces}  Values: {comparators}"
        
        elif node_type == 'BoolOp':
            op = ast_dict.get('op', 'Unknown')
            values = "\n".join([
                self.to_text_tree(val, indent + 1)
                for val in ast_dict.get('values', [])
            ])
            return f"{spaces}{op}:\n{values}"
        
        elif node_type == 'Name':
            return f"{spaces}Field: {ast_dict.get('id', 'unknown')}"
        
        elif node_type == 'Constant':
            return f"{spaces}Value: {ast_dict.get('value', 'unknown')}"
        
        else:
            return f"{spaces}{node_type}: {json.dumps(ast_dict, indent=2)}"
    
    def print_rule_ast(self, rule_id: str) -> None:
        """Print AST tree for a specific rule."""
        ast_tree = self.get_ast_tree(rule_id)
        if ast_tree:
            print(f"\nAST for rule '{rule_id}':")
            print("=" * 50)
            print(self.to_text_tree(ast_tree))
        else:
            print(f"Rule '{rule_id}' not found")
    
    def print_all_asts(self) -> None:
        """Print AST trees for all rules."""
        for rule in self.rules:
            self.print_rule_ast(rule.id) 