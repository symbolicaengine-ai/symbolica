"""
LLM Configuration
================

Simple configuration for LLM integration with sensible defaults.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMConfig:
    """Simple LLM configuration with defaults."""
    
    # Response limits
    default_max_tokens: int = 50
    max_response_length: int = 200
    
    # Request settings  
    default_temperature: float = 0.1
    timeout_seconds: int = 10
    
    # Cost controls
    max_cost_per_execution: float = 0.50
    
    # Safety settings
    max_prompt_length: int = 2000
    
    @classmethod
    def defaults(cls) -> 'LLMConfig':
        """Get default configuration."""
        return cls()
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> 'LLMConfig':
        """Create config from dictionary with defaults for missing values."""
        return cls(
            default_max_tokens=config_dict.get('default_max_tokens', 50),
            max_response_length=config_dict.get('max_response_length', 200),
            default_temperature=config_dict.get('default_temperature', 0.1),
            timeout_seconds=config_dict.get('timeout_seconds', 10),
            max_cost_per_execution=config_dict.get('max_cost_per_execution', 0.50),
            max_prompt_length=config_dict.get('max_prompt_length', 2000)
        ) 