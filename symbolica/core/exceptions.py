"""
Symbolica Exception Hierarchy
=============================

Essential exceptions for AI agent reasoning.
"""

import logging
from typing import Optional, Any, Dict, List
from datetime import datetime


# Configure logger for Symbolica
logger = logging.getLogger('symbolica')


class SymbolicaError(Exception):
    """Base exception for all Symbolica errors."""
    
    def __init__(self, message: str, details: Optional[Any] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details
        self.context = context or {}
        self.timestamp = datetime.now()
        
        # Log all Symbolica errors
        logger.error(f"{self.__class__.__name__}: {message}", 
                    extra={'details': details, 'context': context})
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.details:
            parts.append(f"Details: {self.details}")
        if self.context:
            parts.append(f"Context: {self.context}")
        return " | ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for structured logging."""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'details': self.details,
            'context': self.context,
            'timestamp': self.timestamp.isoformat()
        }


class ValidationError(SymbolicaError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, rule_id: Optional[str] = None, 
                 value: Optional[Any] = None):
        context = {}
        if field:
            context['field'] = field
        if rule_id:
            context['rule_id'] = rule_id
        if value is not None:
            context['invalid_value'] = str(value)
            
        super().__init__(message, context=context)
        self.field = field
        self.rule_id = rule_id
        self.value = value
    
    def __str__(self) -> str:
        parts = []
        if self.rule_id:
            parts.append(f"in rule '{self.rule_id}'")
        if self.field:
            parts.append(f"for field '{self.field}'")
        
        if parts:
            return f"{' '.join(parts)}: {self.message}"
        else:
            return self.message


class ExecutionError(SymbolicaError):
    """Raised when rule execution fails."""
    
    def __init__(self, message: str, rule_id: Optional[str] = None, 
                 iteration: Optional[int] = None, facts: Optional[Dict[str, Any]] = None):
        context = {}
        if rule_id:
            context['rule_id'] = rule_id
        if iteration is not None:
            context['iteration'] = iteration
        if facts:
            context['facts_count'] = len(facts)
            
        super().__init__(message, context=context)
        self.rule_id = rule_id
        self.iteration = iteration
    
    def __str__(self) -> str:
        parts = ["Execution error"]
        if self.rule_id:
            parts.append(f"in rule '{self.rule_id}'")
        if self.iteration is not None:
            parts.append(f"at iteration {self.iteration}")
        parts.append(f": {self.message}")
        return " ".join(parts)


class EvaluationError(ExecutionError):
    """Raised when condition evaluation fails."""
    
    def __init__(self, message: str, expression: Optional[str] = None, 
                 rule_id: Optional[str] = None, field_values: Optional[Dict[str, Any]] = None):
        context = {}
        if expression:
            context['expression'] = expression
        if field_values:
            context['field_values'] = field_values
            
        super().__init__(message, rule_id=rule_id)
        self.expression = expression
        self.field_values = field_values or {}
    
    def __str__(self) -> str:
        parts = ["Evaluation error"]
        if self.rule_id:
            parts.append(f"in rule '{self.rule_id}'")
        parts.append(f": {self.message}")
        if self.expression:
            parts.append(f"Expression: {self.expression}")
        return " | ".join(parts)


class ConfigurationError(SymbolicaError):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, 
                 config_value: Optional[Any] = None):
        context = {}
        if config_key:
            context['config_key'] = config_key
        if config_value is not None:
            context['config_value'] = str(config_value)
            
        super().__init__(message, context=context)
        self.config_key = config_key
        self.config_value = config_value


class FunctionError(SymbolicaError):
    """Raised when custom function operations fail."""
    
    def __init__(self, message: str, function_name: Optional[str] = None, 
                 args: Optional[List[Any]] = None, original_error: Optional[Exception] = None):
        context = {}
        if function_name:
            context['function_name'] = function_name
        if args is not None:
            context['args'] = [str(arg) for arg in args]
        if original_error:
            context['original_error'] = str(original_error)
            
        super().__init__(message, details=original_error, context=context)
        self.function_name = function_name
        self.args = args
        self.original_error = original_error


class SecurityError(EvaluationError):
    """Raised when expression violates security constraints."""
    
    def __init__(self, message: str, expression: Optional[str] = None, 
                 rule_id: Optional[str] = None, violation_type: Optional[str] = None):
        context = {}
        if violation_type:
            context['violation_type'] = violation_type
            
        super().__init__(message, expression=expression, rule_id=rule_id, field_values=context)
        self.violation_type = violation_type


class DAGError(SymbolicaError):
    """Raised when DAG operations fail."""
    
    def __init__(self, message: str, rule_ids: Optional[List[str]] = None, 
                 cycle_rules: Optional[List[str]] = None):
        context = {}
        if rule_ids:
            context['affected_rules'] = rule_ids
        if cycle_rules:
            context['cycle_rules'] = cycle_rules
            
        super().__init__(message, context=context)
        self.rule_ids = rule_ids or []
        self.cycle_rules = cycle_rules or []


class TemporalError(SymbolicaError):
    """Raised when temporal operations fail."""
    
    def __init__(self, message: str, key: Optional[str] = None, 
                 timestamp: Optional[float] = None):
        context = {}
        if key:
            context['temporal_key'] = key
        if timestamp is not None:
            context['timestamp'] = timestamp
            
        super().__init__(message, context=context)
        self.key = key
        self.timestamp = timestamp


# Error aggregation utilities
class ErrorCollector:
    """Collects multiple errors for batch operations."""
    
    def __init__(self):
        self.errors: List[SymbolicaError] = []
        self.warnings: List[str] = []
    
    def add_error(self, error: SymbolicaError) -> None:
        """Add an error to the collection."""
        self.errors.append(error)
        logger.error(f"Collected error: {error}")
    
    def add_warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Add a warning to the collection."""
        warning = f"{message}"
        if context:
            warning += f" | Context: {context}"
        self.warnings.append(warning)
        logger.warning(warning)
    
    def has_errors(self) -> bool:
        """Check if any errors were collected."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if any warnings were collected."""
        return len(self.warnings) > 0
    
    def raise_if_errors(self, summary_message: str = "Multiple errors occurred") -> None:
        """Raise an exception if any errors were collected."""
        if self.has_errors():
            error_details = [str(error) for error in self.errors]
            raise SymbolicaError(
                f"{summary_message}: {len(self.errors)} error(s)",
                details=error_details,
                context={'error_count': len(self.errors), 'warning_count': len(self.warnings)}
            )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of collected errors and warnings."""
        return {
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': [error.to_dict() for error in self.errors],
            'warnings': self.warnings
        }


# Logging configuration helper
def configure_symbolica_logging(level: str = 'WARNING', 
                               format_string: Optional[str] = None) -> None:
    """Configure logging for Symbolica with structured format."""
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=[logging.StreamHandler()]
    )
    
    # Set Symbolica logger level
    logger.setLevel(getattr(logging, level.upper()))