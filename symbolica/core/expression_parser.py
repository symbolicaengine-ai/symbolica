"""
Expression Parser
================

Simple parser for handling expression detection and template evaluation.
Extracted from Engine class to fix mixed abstraction levels anti-pattern.
"""

import re
import logging
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ExecutionContext

logger = logging.getLogger(__name__)


class ExpressionParser:
    """
    Simple expression parser for detecting and evaluating expressions and templates.
    
    Handles:
    - Expression detection (arithmetic, comparisons, functions)
    - Template evaluation ({{ variable }} syntax)
    - Action value evaluation
    """
    
    def __init__(self, evaluator=None):
        """Initialize with optional evaluator."""
        self._evaluator = evaluator
        self._logger = logging.getLogger(f'{__name__}.ExpressionParser')
    
    def is_expression(self, value: Any) -> bool:
        """Detect if a value should be treated as an expression to evaluate."""
        if not isinstance(value, str):
            return False
        
        # Skip empty strings
        if not value.strip():
            return False
        
        # Check for arithmetic operators
        arithmetic_ops = ['+', '-', '*', '/', '//', '%', '**']
        has_arithmetic = any(op in value for op in arithmetic_ops)
        
        # Check for parentheses (likely mathematical expression)
        has_parentheses = '(' in value and ')' in value
        
        # Check for function calls (word followed by parentheses)
        has_function_call = re.search(r'\w+\s*\(', value)
        
        # Check for comparison operators 
        comparison_ops = ['==', '!=', '<', '>', '<=', '>=']
        has_comparisons = any(op in value for op in comparison_ops)
        
        # Check for template variables ({{ variable }})
        has_templates = '{{' in value and '}}' in value
        
        # Check for boolean/logical operators, but be more careful about context
        # Only consider it logical if it's combined with other expression indicators
        logical_ops = [' and ', ' or ', ' not ', ' in ', ' is ']
        has_logical_words = any(op in value for op in logical_ops)
        
        # More restrictive logical check: must have logical words AND other expression indicators
        # This prevents simple sentences like "Good credit and sufficient income" from being treated as expressions
        has_logical = has_logical_words and (has_arithmetic or has_parentheses or has_function_call or has_comparisons or has_templates)
        
        # Only treat as expression if it has clear expression indicators
        # Do NOT treat single words or simple sentences as expressions
        is_likely_expression = (
            has_arithmetic or 
            has_parentheses or 
            has_function_call or
            has_comparisons or
            has_templates or
            has_logical
        )
        
        # Additional checks to avoid false positives
        # Skip if it's clearly a sentence (multiple words with spaces and no operators)
        # BUT don't exclude template expressions even if they have spaces
        if (' ' in value and 
            not any(op in value for op in arithmetic_ops + comparison_ops) and 
            not has_parentheses and 
            not has_templates and
            not has_function_call and
            not has_logical):  # Updated to use the more restrictive has_logical
            return False
        
        # Skip if it looks like a URL, file path, or other string literal
        # Don't exclude template expressions or arithmetic expressions
        if (any(pattern in value.lower() for pattern in ['http://', 'https://', '\\\\', '.com', '.org']) or 
            ('/' in value and not has_templates and not has_arithmetic and ' ' not in value)):
            return False
        
        return is_likely_expression
    
    def evaluate_action_value(self, value: Any, context: 'ExecutionContext') -> Any:
        """Evaluate an action value, handling both templates and expressions."""
        # Only attempt evaluation for potential expressions
        if not self.is_expression(value):
            return value
        
        try:
            value_str = str(value)
            
            # Handle template expressions like {{ variable }} or {{ expression }}
            if '{{' in value_str and '}}' in value_str:
                return self.evaluate_template_expression(value_str, context)
            
            # Handle direct expressions (arithmetic, comparisons, function calls)
            else:
                if self._evaluator and hasattr(self._evaluator, '_core'):
                    result, _ = self._evaluator._core.evaluate(value_str, context)
                    return result
                else:
                    # Fallback: return original value if no evaluator
                    return value
                
        except Exception as e:
            # If evaluation fails, return original value
            # This ensures backward compatibility
            self._logger.debug(f"Expression evaluation failed for '{value}': {e}")
            return value
    
    def evaluate_template_expression(self, template: str, context: 'ExecutionContext') -> Any:
        """Evaluate template expressions with variable substitution."""
        import re
        
        # Pattern to match {{ expression }} - use non-greedy match to handle nested braces
        template_pattern = r'\{\{\s*(.*?)\s*\}\}'
        
        # Find all template expressions
        matches = list(re.finditer(template_pattern, template))
        
        if not matches:
            # No template expressions found, return as-is
            return template
        
        # If the entire string is a single template expression, evaluate and return the result
        if len(matches) == 1 and matches[0].group(0).strip() == template.strip():
            expression = matches[0].group(1).strip()
            try:
                # Use the core evaluator which properly handles PROMPT function
                if self._evaluator and hasattr(self._evaluator, '_core'):
                    result, _ = self._evaluator._core.evaluate(expression, context)
                    return result
                else:
                    # Fallback: return the expression itself
                    return expression
            except Exception as e:
                # If evaluation fails, return the expression itself
                self._logger.debug(f"Template evaluation failed for '{expression}': {e}")
                return expression
        
        # Multiple templates or mixed content - perform string substitution
        result = template
        for match in reversed(matches):  # Process in reverse to maintain positions
            expression = match.group(1).strip()
            try:
                # Use the core evaluator which properly handles PROMPT function
                if self._evaluator and hasattr(self._evaluator, '_core'):
                    eval_result, _ = self._evaluator._core.evaluate(expression, context)
                    # Convert result to string for substitution
                    result = result[:match.start()] + str(eval_result) + result[match.end():]
                else:
                    # If evaluation fails, substitute with the expression itself
                    result = result[:match.start()] + expression + result[match.end():]
            except Exception as e:
                # If evaluation fails, substitute with the expression itself
                self._logger.debug(f"Template substitution failed for '{expression}': {e}")
                result = result[:match.start()] + expression + result[match.end():]
        
        return result 