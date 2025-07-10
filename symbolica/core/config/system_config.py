"""
System Configuration
====================

Centralized system-wide configuration and constants.
Eliminates hard-coded magic numbers and constants scattered throughout codebase.
"""

from typing import Dict, Any


class SystemConfig:
    """Centralized system configuration and constants."""
    
    # Engine Configuration
    DEFAULT_MAX_ITERATIONS: int = 100
    DEFAULT_RULE_PRIORITY: int = 100
    PERFORMANCE_THRESHOLD_MS: float = 1000.0  # Performance warning threshold
    
    # Validation Configuration
    MAX_RULE_DEPTH: int = 50  # Maximum nesting depth for rule validation
    MAX_CONDITION_LENGTH: int = 1000  # Maximum characters in condition string
    MAX_RULES_PER_FILE: int = 1000  # Maximum rules in a single YAML file
    
    # Execution Configuration
    DEFAULT_TIMEOUT_SECONDS: int = 30  # Default execution timeout
    MAX_FACT_VALUE_LENGTH: int = 10000  # Maximum length for fact values
    MAX_EXECUTION_STEPS: int = 10000  # Maximum steps in execution path
    
    # Memory Configuration
    MAX_CONTEXT_SIZE_MB: int = 100  # Maximum context size in memory
    MAX_TRACE_ENTRIES: int = 1000  # Maximum trace entries to store
    CACHE_SIZE_LIMIT: int = 10000  # Maximum items in caches
    
    # String Formatting Configuration
    MAX_ERROR_MESSAGE_LENGTH: int = 2000  # Maximum error message length
    DOCUMENTATION_LINE_WIDTH: int = 80  # Line width for documentation
    KEYWORDS_PER_DOC_LINE: int = 6  # Keywords per line in documentation
    SAMPLE_KEYWORDS_COUNT: int = 30  # Sample keywords to show in docs
    
    # File and Path Configuration
    DEFAULT_ENCODING: str = 'utf-8'
    YAML_FILE_EXTENSIONS: tuple = ('.yaml', '.yml')
    MAX_FILE_SIZE_MB: int = 10  # Maximum YAML file size
    
    # Logging Configuration
    DEFAULT_LOG_LEVEL: str = 'INFO'
    MAX_LOG_MESSAGE_LENGTH: int = 1000
    LOG_CONTEXT_FIELDS: int = 5  # Maximum context fields in log entries
    
    # Performance Configuration
    BENCHMARK_ITERATIONS: int = 1000  # Iterations for performance benchmarks
    SLOW_OPERATION_THRESHOLD_MS: float = 100.0  # Threshold for slow operations
    MEMORY_WARNING_THRESHOLD_MB: int = 50  # Memory usage warning threshold
    
    @classmethod
    def get_all_constants(cls) -> Dict[str, Any]:
        """Get all configuration constants as a dictionary.
        
        Returns:
            Dictionary of all configuration constants
        """
        return {
            name: value for name, value in cls.__dict__.items()
            if not name.startswith('_') and not callable(value)
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate that configuration values are reasonable.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate positive integers
        positive_int_fields = [
            'DEFAULT_MAX_ITERATIONS', 'DEFAULT_RULE_PRIORITY', 'MAX_RULE_DEPTH',
            'MAX_CONDITION_LENGTH', 'MAX_RULES_PER_FILE', 'DEFAULT_TIMEOUT_SECONDS',
            'MAX_FACT_VALUE_LENGTH', 'MAX_EXECUTION_STEPS', 'MAX_CONTEXT_SIZE_MB',
            'MAX_TRACE_ENTRIES', 'CACHE_SIZE_LIMIT', 'MAX_ERROR_MESSAGE_LENGTH',
            'DOCUMENTATION_LINE_WIDTH', 'KEYWORDS_PER_DOC_LINE', 'SAMPLE_KEYWORDS_COUNT',
            'MAX_FILE_SIZE_MB', 'MAX_LOG_MESSAGE_LENGTH', 'LOG_CONTEXT_FIELDS',
            'BENCHMARK_ITERATIONS', 'MEMORY_WARNING_THRESHOLD_MB'
        ]
        
        for field in positive_int_fields:
            value = getattr(cls, field)
            if not isinstance(value, int) or value <= 0:
                raise ValueError(f"{field} must be a positive integer, got {value}")
        
        # Validate positive floats
        positive_float_fields = [
            'PERFORMANCE_THRESHOLD_MS', 'SLOW_OPERATION_THRESHOLD_MS'
        ]
        
        for field in positive_float_fields:
            value = getattr(cls, field)
            if not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"{field} must be a positive number, got {value}")
        
        # Validate strings
        string_fields = ['DEFAULT_ENCODING', 'DEFAULT_LOG_LEVEL']
        for field in string_fields:
            value = getattr(cls, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string, got {value}")
        
        return True 