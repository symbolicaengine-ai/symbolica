"""
Symbolica Exception Hierarchy
=============================

Essential exceptions for AI agent reasoning.
"""

from typing import Optional, Any


class SymbolicaError(Exception):
    """Base exception for all Symbolica errors."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.details = details
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class ValidationError(SymbolicaError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.field = field
    
    def __str__(self) -> str:
        if self.field:
            return f"Validation error for field '{self.field}': {self.message}"
        return f"Validation error: {self.message}"


class ExecutionError(SymbolicaError):
    """Raised when rule execution fails."""
    
    def __init__(self, message: str, rule_id: Optional[str] = None):
        super().__init__(message)
        self.rule_id = rule_id
    
    def __str__(self) -> str:
        if self.rule_id:
            return f"Execution error in rule '{self.rule_id}': {self.message}"
        return f"Execution error: {self.message}"


class EvaluationError(ExecutionError):
    """Raised when condition evaluation fails."""
    
    def __init__(self, message: str, expression: Optional[str] = None, rule_id: Optional[str] = None):
        super().__init__(message, rule_id)
        self.expression = expression
    
    def __str__(self) -> str:
        parts = [f"Evaluation error: {self.message}"]
        if self.expression:
            parts.append(f"Expression: {self.expression}")
        if self.rule_id:
            parts.append(f"Rule: {self.rule_id}")
        return " | ".join(parts)