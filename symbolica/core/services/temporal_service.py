"""
Temporal Service
================

Manages temporal operations and function registration.
Separated from Engine to follow Single Responsibility Principle.
"""

from typing import Dict, Any, Optional
from .function_registry import FunctionRegistry
from ..._internal.storage.temporal_store import TemporalStore


class TemporalService:
    """Manages temporal operations and function registration."""
    
    def __init__(self, 
                 max_age_seconds: int = 3600,
                 max_points_per_key: int = 1000,
                 cleanup_interval: int = 300):
        """Initialize temporal service.
        
        Args:
            max_age_seconds: Maximum age of time-series data (default: 1 hour)
            max_points_per_key: Maximum points stored per time-series key
            cleanup_interval: How often to run cleanup (seconds)
        """
        self._store = TemporalStore(
            max_age_seconds=max_age_seconds,
            max_points_per_key=max_points_per_key,
            cleanup_interval=cleanup_interval
        )
    
    def register_temporal_functions(self, function_registry: FunctionRegistry) -> None:
        """Register all temporal functions with the function registry.
        
        Args:
            function_registry: Function registry to register with
        """
        # Time-series aggregation functions
        # Use register_system_function since these are built-in system functions
        function_registry.register_system_function(
            "recent_avg", 
            lambda key, duration: self._store.avg_in_window(key, duration)
        )
        function_registry.register_system_function(
            "recent_max", 
            lambda key, duration: self._store.max_in_window(key, duration)
        )
        function_registry.register_system_function(
            "recent_min", 
            lambda key, duration: self._store.min_in_window(key, duration)
        )
        function_registry.register_system_function(
            "recent_count", 
            lambda key, duration: self._store.count_in_window(key, duration)
        )
        
        # Sustained condition functions
        function_registry.register_system_function(
            "sustained", 
            lambda key, threshold, duration: self._store.sustained_condition(key, threshold, duration, '>')
        )
        function_registry.register_system_function(
            "sustained_above", 
            lambda key, threshold, duration: self._store.sustained_condition(key, threshold, duration, '>')
        )
        function_registry.register_system_function(
            "sustained_below", 
            lambda key, threshold, duration: self._store.sustained_condition(key, threshold, duration, '<')
        )
        
        # TTL fact functions
        function_registry.register_system_function(
            "ttl_fact", 
            lambda key: self._store.get_ttl_fact(key)
        )
        function_registry.register_system_function(
            "has_ttl_fact", 
            lambda key: self._store.get_ttl_fact(key) is not None
        )
    
    def store_datapoint(self, key: str, value: float, timestamp: Optional[float] = None) -> None:
        """Store a time-series data point for use in temporal functions.
        
        Args:
            key: Metric key (e.g., 'cpu_utilization', 'error_rate')
            value: Numeric value
            timestamp: Optional timestamp (defaults to current time)
            
        Example:
            service.store_datapoint("cpu_utilization", 85.2)
            service.store_datapoint("response_time", 450)
        """
        self._store.store_datapoint(key, value, timestamp)
    
    def set_ttl_fact(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Set a fact with time-to-live (TTL).
        
        Args:
            key: Fact key
            value: Fact value (any type)
            ttl_seconds: Time to live in seconds
            
        Example:
            service.set_ttl_fact("maintenance_mode", True, 3600)  # 1 hour
            service.set_ttl_fact("user_session", user_data, 1800)  # 30 minutes
        """
        self._store.set_ttl_fact(key, value, ttl_seconds)
    
    def get_ttl_fact(self, key: str) -> Optional[Any]:
        """Get a TTL fact if it exists and hasn't expired.
        
        Args:
            key: Fact key
            
        Returns:
            Fact value if exists and not expired, None otherwise
        """
        return self._store.get_ttl_fact(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get temporal store statistics.
        
        Returns:
            Dictionary with statistics about temporal storage
        """
        return self._store.get_stats()
    
    def cleanup_old_data(self) -> Dict[str, int]:
        """Force cleanup of old temporal data.
        
        Returns:
            Dictionary with cleanup statistics
        """
        return self._store.cleanup_old_data()
    
    def clear_all_data(self) -> None:
        """Clear all temporal data (time-series and TTL facts).
        
        Warning:
            This will remove all stored temporal data.
        """
        # Clear time-series data
        self._store._timeseries.clear()
        
        # Clear TTL facts
        self._store._ttl_facts.clear()
    
    def get_time_series_keys(self) -> list:
        """Get all time-series keys currently stored.
        
        Returns:
            List of time-series keys
        """
        return list(self._store._timeseries.keys())
    
    def get_ttl_fact_keys(self) -> list:
        """Get all TTL fact keys currently stored.
        
        Returns:
            List of TTL fact keys
        """
        return list(self._store._ttl_facts.keys())
    
    def has_time_series_data(self, key: str) -> bool:
        """Check if time-series data exists for a key.
        
        Args:
            key: Time-series key
            
        Returns:
            True if data exists for the key
        """
        return key in self._store._timeseries and len(self._store._timeseries[key]) > 0
    
    def has_ttl_fact(self, key: str) -> bool:
        """Check if a TTL fact exists and is not expired.
        
        Args:
            key: Fact key
            
        Returns:
            True if fact exists and is not expired
        """
        return self._store.get_ttl_fact(key) is not None
    
    def get_data_point_count(self, key: str) -> int:
        """Get number of data points for a time-series key.
        
        Args:
            key: Time-series key
            
        Returns:
            Number of data points
        """
        if key not in self._store._timeseries:
            return 0
        return len(self._store._timeseries[key]) 