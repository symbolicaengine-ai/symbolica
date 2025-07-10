"""
Function Registry
=================

Manages custom function registration and validation.
Separated from Engine to follow Single Responsibility Principle.
"""

from typing import Dict, Callable, Any, List
from .exceptions import ValidationError
from .schema_validator import SchemaValidator


class FunctionRegistry:
    """Manages registration and validation of custom functions."""
    
    def __init__(self):
        self._functions: Dict[str, Callable] = {}
        self._schema_validator = SchemaValidator()
    
    @property
    def reserved_words(self) -> frozenset:
        """Get reserved words from the schema validator."""
        return self._schema_validator.get_reserved_keywords()
    
    def register_function(self, name: str, func: Callable, allow_unsafe: bool = False) -> None:
        """Register a custom function for use in rule conditions.
        
        Args:
            name: Function name to use in conditions
            func: Callable function (lambda recommended for safety)
            allow_unsafe: If True, allows full functions (use with caution)
            
        Safety:
            By default, only lambda functions are recommended for safety.
            Full functions can hang the engine, consume memory, or have side effects.
            Use allow_unsafe=True only if you trust the function completely.
            
        Example:
            # Safe (recommended)
            registry.register_function("risk_score", lambda score: 
                "low" if score > 750 else "high" if score < 600 else "medium")
            
            # Unsafe (use with caution)
            def complex_calc(x, y, z):
                return x * y + z
            registry.register_function("complex_calc", complex_calc, allow_unsafe=True)
            
        Raises:
            ValidationError: If function name is invalid or function is unsafe
        """
        # Validate function
        if not callable(func):
            raise ValidationError(f"Function '{name}' must be callable")
        
        # Use schema validator for consistent validation (but allow system functions to bypass)
        if not allow_unsafe:
            # For user functions, enforce all validation including reserved keywords
            self._schema_validator.validate_identifier(name, f"Function name '{name}'")
            
            # Safety checks for user functions
            if not self._is_lambda(func):
                raise ValidationError(
                    f"Function '{name}' is not a lambda. "
                    f"For safety, only lambda functions are allowed by default. "
                    f"Use allow_unsafe=True if you trust this function completely. "
                    f"Note: Unsafe functions can hang the engine, consume memory, or have side effects."
                )
        else:
            # For system functions (allow_unsafe=True), only validate basic identifier rules
            if not isinstance(name, str) or not name.strip():
                raise ValidationError(f"Function name must be a non-empty string")
            if not name.isidentifier():
                raise ValidationError(f"Function name '{name}' must be a valid identifier")
        
        # Register the function
        self._functions[name] = func
    
    def unregister_function(self, name: str) -> None:
        """Remove a registered custom function.
        
        Args:
            name: Function name to remove
        """
        if name in self._functions:
            del self._functions[name]
    
    def get_function(self, name: str) -> Callable:
        """Get a registered function by name.
        
        Args:
            name: Function name
            
        Returns:
            The registered function
            
        Raises:
            ValidationError: If function is not registered
        """
        if name not in self._functions:
            raise ValidationError(f"Function '{name}' is not registered")
        return self._functions[name]
    
    def has_function(self, name: str) -> bool:
        """Check if a function is registered.
        
        Args:
            name: Function name
            
        Returns:
            True if function is registered
        """
        return name in self._functions
    
    def list_functions(self) -> List[str]:
        """Get list of all registered function names.
        
        Returns:
            List of function names
        """
        return list(self._functions.keys())
    
    def clear_functions(self) -> None:
        """Remove all registered functions."""
        self._functions.clear()
    
    def _is_lambda(self, func: Callable) -> bool:
        """Check if a function is a lambda."""
        try:
            return func.__name__ == '<lambda>'
        except AttributeError:
            # Some callable objects might not have __name__
            return False
    
    def call_function(self, name: str, *args: Any) -> Any:
        """Call a registered function with error handling.
        
        Args:
            name: Function name
            *args: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            ValidationError: If function is not registered or call fails
        """
        if name not in self._functions:
            raise ValidationError(f"Function '{name}' is not registered")
        
        try:
            return self._functions[name](*args)
        except Exception as e:
            raise ValidationError(f"Error calling function '{name}': {e}")
    
    def validate_function_call(self, name: str, arg_count: int) -> bool:
        """Validate that a function call would be valid.
        
        Args:
            name: Function name
            arg_count: Number of arguments
            
        Returns:
            True if call would be valid
        """
        if name not in self._functions:
            return False
        
        # For now, just check if function exists
        # Could add argument count validation in the future
        return True 