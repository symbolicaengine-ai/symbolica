"""
Engine Configuration
====================

Simple configuration class to centralize scattered configuration parameters.
Fixes the scattered configuration anti-pattern without overengineering.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class EngineConfig:
    """
    Simple configuration for the Symbolica Engine.
    
    Centralizes all configuration parameters instead of having them scattered
    across multiple dictionaries and parameters.
    """
    
    # Execution configuration
    max_iterations: int = 10
    fallback_strategy: str = "strict"  # "strict" or "auto"
    
    # Temporal configuration
    temporal_max_age_seconds: int = 3600
    temporal_max_points_per_key: int = 1000
    temporal_cleanup_interval: int = 300
    
    # LLM configuration
    llm_max_tokens: int = 1000
    llm_temperature: float = 0.0
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 3
    llm_cost_limit_per_hour: float = 10.0
    
    @classmethod
    def from_dicts(cls, 
                   temporal_config: Optional[Dict[str, Any]] = None,
                   execution_config: Optional[Dict[str, Any]] = None,
                   llm_config: Optional[Dict[str, Any]] = None,
                   fallback_strategy: str = "strict") -> 'EngineConfig':
        """
        Create configuration from the old dictionary-based parameters.
        
        This provides backward compatibility with the existing Engine constructor.
        """
        temporal_config = temporal_config or {}
        execution_config = execution_config or {}
        llm_config = llm_config or {}
        
        return cls(
            # Execution
            max_iterations=execution_config.get('max_iterations', 10),
            fallback_strategy=fallback_strategy,
            
            # Temporal  
            temporal_max_age_seconds=temporal_config.get('max_age_seconds', 3600),
            temporal_max_points_per_key=temporal_config.get('max_points_per_key', 1000),
            temporal_cleanup_interval=temporal_config.get('cleanup_interval', 300),
            
            # LLM
            llm_max_tokens=llm_config.get('max_tokens', 1000),
            llm_temperature=llm_config.get('temperature', 0.0),
            llm_timeout_seconds=llm_config.get('timeout_seconds', 30),
            llm_max_retries=llm_config.get('max_retries', 3),
            llm_cost_limit_per_hour=llm_config.get('cost_limit_per_hour', 10.0),
        )
    
    def get_temporal_config(self) -> Dict[str, Any]:
        """Get temporal configuration as dictionary (for TemporalService constructor)."""
        return {
            'max_age_seconds': self.temporal_max_age_seconds,
            'max_points_per_key': self.temporal_max_points_per_key,
            'cleanup_interval': self.temporal_cleanup_interval
        }
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration as dictionary (for LLM components)."""
        return {
            'max_tokens': self.llm_max_tokens,
            'temperature': self.llm_temperature,
            'timeout_seconds': self.llm_timeout_seconds,
            'max_retries': self.llm_max_retries,
            'cost_limit_per_hour': self.llm_cost_limit_per_hour
        }
    
    def validate(self) -> None:
        """Simple validation of configuration values."""
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive")
        
        if self.fallback_strategy not in ["strict", "auto"]:
            raise ValueError("fallback_strategy must be 'strict' or 'auto'")
        
        if self.temporal_max_age_seconds <= 0:
            raise ValueError("temporal_max_age_seconds must be positive")
        
        if self.temporal_max_points_per_key <= 0:
            raise ValueError("temporal_max_points_per_key must be positive")
        
        if self.llm_temperature < 0.0 or self.llm_temperature > 2.0:
            raise ValueError("llm_temperature must be between 0.0 and 2.0") 