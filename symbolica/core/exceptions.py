"""
Symbolica Exception Hierarchy
=============================

Clean, well-organized exceptions for different error conditions.
"""

from typing import Optional, List, Any


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
    """Raised when validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, 
                 value: Optional[Any] = None):
        super().__init__(message)
        self.field = field
        self.value = value
    
    def __str__(self) -> str:
        if self.field:
            return f"Validation error for field '{self.field}': {self.message}"
        return f"Validation error: {self.message}"


class CompilationError(SymbolicaError):
    """Raised when rule compilation fails."""
    
    def __init__(self, message: str, source: Optional[str] = None,
                 line: Optional[int] = None, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.source = source
        self.line = line
        self.errors = errors or []
    
    def __str__(self) -> str:
        parts = [f"Compilation error: {self.message}"]
        if self.source:
            parts.append(f"Source: {self.source}")
        if self.line:
            parts.append(f"Line: {self.line}")
        if self.errors:
            parts.append(f"Errors: {'; '.join(self.errors)}")
        return " | ".join(parts)


class ExecutionError(SymbolicaError):
    """Raised when rule execution fails."""
    
    def __init__(self, message: str, rule_id: Optional[str] = None,
                 context_id: Optional[str] = None):
        super().__init__(message)
        self.rule_id = rule_id
        self.context_id = context_id
    
    def __str__(self) -> str:
        parts = [f"Execution error: {self.message}"]
        if self.rule_id:
            parts.append(f"Rule: {self.rule_id}")
        if self.context_id:
            parts.append(f"Context: {self.context_id}")
        return " | ".join(parts)


class EvaluationError(ExecutionError):
    """Raised when condition evaluation fails."""
    
    def __init__(self, message: str, expression: Optional[str] = None,
                 rule_id: Optional[str] = None):
        super().__init__(message, rule_id)
        self.expression = expression
    
    def __str__(self) -> str:
        parts = [f"Evaluation error: {self.message}"]
        if self.expression:
            parts.append(f"Expression: {self.expression}")
        if self.rule_id:
            parts.append(f"Rule: {self.rule_id}")
        return " | ".join(parts)


class ActionExecutionError(ExecutionError):
    """Raised when action execution fails."""
    
    def __init__(self, message: str, action_type: Optional[str] = None,
                 rule_id: Optional[str] = None):
        super().__init__(message, rule_id)
        self.action_type = action_type
    
    def __str__(self) -> str:
        parts = [f"Action execution error: {self.message}"]
        if self.action_type:
            parts.append(f"Action: {self.action_type}")
        if self.rule_id:
            parts.append(f"Rule: {self.rule_id}")
        return " | ".join(parts)


class LoadError(SymbolicaError):
    """Raised when loading rules fails."""
    
    def __init__(self, message: str, source: Optional[str] = None,
                 format: Optional[str] = None):
        super().__init__(message)
        self.source = source
        self.format = format
    
    def __str__(self) -> str:
        parts = [f"Load error: {self.message}"]
        if self.source:
            parts.append(f"Source: {self.source}")
        if self.format:
            parts.append(f"Format: {self.format}")
        return " | ".join(parts)


class CacheError(SymbolicaError):
    """Raised when caching operations fail."""
    pass


class ConfigurationError(SymbolicaError):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str, parameter: Optional[str] = None,
                 value: Optional[Any] = None):
        super().__init__(message)
        self.parameter = parameter
        self.value = value
    
    def __str__(self) -> str:
        if self.parameter:
            return f"Configuration error for '{self.parameter}': {self.message}"
        return f"Configuration error: {self.message}" 