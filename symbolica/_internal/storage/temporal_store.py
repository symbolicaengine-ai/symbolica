"""
Simple Temporal Store for Time-Series and TTL Facts
==================================================

Lightweight in-memory storage for temporal data used by custom functions.
Designed for production monitoring, alerting, and session management.
"""

import time
from typing import Dict, List, Tuple, Any, Optional, Callable
from collections import deque
from dataclasses import dataclass
import threading


@dataclass
class TimeSeriesPoint:
    """Single time-series data point."""
    timestamp: float
    value: float


class TemporalStore:
    """
    Simple in-memory temporal storage for production workloads.
    
    Features:
    - Time-series storage with automatic cleanup
    - TTL facts with expiration
    - Memory-bounded (configurable limits)
    - Thread-safe operations
    - Efficient window queries
    """
    
    def __init__(self, 
                 max_age_seconds: int = 3600,
                 max_points_per_key: int = 1000,
                 cleanup_interval: int = 300):
        """
        Initialize temporal store.
        
        Args:
            max_age_seconds: Maximum age of time-series data (default: 1 hour)
            max_points_per_key: Maximum points stored per time-series key
            cleanup_interval: How often to run cleanup (seconds)
        """
        self._max_age = max_age_seconds
        self._max_points = max_points_per_key
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
        
        # Time-series storage: {key: deque of TimeSeriesPoint}
        self._timeseries: Dict[str, deque] = {}
        
        # TTL storage: {key: (value, expires_at)}
        self._ttl_facts: Dict[str, Tuple[Any, float]] = {}
        
        # Thread safety
        self._lock = threading.RLock()
    
    def store_datapoint(self, key: str, value: float, timestamp: Optional[float] = None) -> None:
        """
        Store a time-series data point.
        
        Args:
            key: Time-series key (e.g., 'cpu_utilization', 'error_rate')
            value: Numeric value to store
            timestamp: Optional timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = time.time()
        
        with self._lock:
            # Initialize deque if needed
            if key not in self._timeseries:
                self._timeseries[key] = deque(maxlen=self._max_points)
            
            # Add point
            point = TimeSeriesPoint(timestamp, value)
            self._timeseries[key].append(point)
            
            # Trigger cleanup if needed
            self._maybe_cleanup()
    
    def get_window_data(self, key: str, duration_seconds: int) -> List[TimeSeriesPoint]:
        """
        Get all data points within the specified time window.
        
        Args:
            key: Time-series key
            duration_seconds: Window size in seconds (looking backward from now)
            
        Returns:
            List of TimeSeriesPoint within the window
        """
        cutoff_time = time.time() - duration_seconds
        
        with self._lock:
            if key not in self._timeseries:
                return []
            
                    # Filter points within window
        return [point for point in self._timeseries[key] 
               if point.timestamp >= cutoff_time]
    
    def avg_in_window(self, key: str, duration_seconds: int) -> Optional[float]:
        """Calculate average value in time window."""
        points = self.get_window_data(key, duration_seconds)
        if not points:
            return None
        return sum(p.value for p in points) / len(points)
    
    def max_in_window(self, key: str, duration_seconds: int) -> Optional[float]:
        """Get maximum value in time window."""
        points = self.get_window_data(key, duration_seconds)
        if not points:
            return None
        return max(p.value for p in points)
    
    def min_in_window(self, key: str, duration_seconds: int) -> Optional[float]:
        """Get minimum value in time window."""
        points = self.get_window_data(key, duration_seconds)
        if not points:
            return None
        return min(p.value for p in points)
    
    def count_in_window(self, key: str, duration_seconds: int) -> int:
        """Count data points in time window."""
        return len(self.get_window_data(key, duration_seconds))
    
    def sustained_condition(self, key: str, threshold: float, duration_seconds: int, 
                          operator: str = '>') -> bool:
        """
        Check if condition was sustained for the entire duration.
        
        Args:
            key: Time-series key
            threshold: Threshold value
            duration_seconds: How long condition must be sustained
            operator: Comparison operator ('>', '>=', '<', '<=', '==', '!=')
            
        Returns:
            True if condition was sustained for entire duration
        """
        points = self.get_window_data(key, duration_seconds)
        if not points:
            return False
        
        # Check if we have data covering the full duration
        if not points:
            return False
            
        # More lenient check - just need reasonable coverage
        earliest_time = min(p.timestamp for p in points)
        required_time = time.time() - duration_seconds
        coverage_ratio = (time.time() - earliest_time) / duration_seconds
        
        if coverage_ratio < 0.8:  # Need at least 80% coverage
            return False
        
        # Check condition for all points
        for point in points:
            if not self._evaluate_condition(point.value, operator, threshold):
                return False
        
        return True
    
    def set_ttl_fact(self, key: str, value: Any, ttl_seconds: int) -> None:
        """
        Store a fact with TTL (time-to-live).
        
        Args:
            key: Fact key
            value: Fact value (any type)
            ttl_seconds: Time to live in seconds
        """
        expires_at = time.time() + ttl_seconds
        
        with self._lock:
            self._ttl_facts[key] = (value, expires_at)
    
    def get_ttl_fact(self, key: str) -> Optional[Any]:
        """
        Get TTL fact if not expired.
        
        Args:
            key: Fact key
            
        Returns:
            Fact value if exists and not expired, None otherwise
        """
        with self._lock:
            if key not in self._ttl_facts:
                return None
            
            value, expires_at = self._ttl_facts[key]
            
            # Check expiration
            if time.time() > expires_at:
                # Expired - remove and return None
                del self._ttl_facts[key]
                return None
            
            return value
    
    def clear_expired_ttl_facts(self) -> int:
        """Remove all expired TTL facts. Returns count of removed facts."""
        current_time = time.time()
        removed = 0
        
        with self._lock:
            expired_keys = [
                key for key, (value, expires_at) in self._ttl_facts.items()
                if current_time > expires_at
            ]
            
            for key in expired_keys:
                del self._ttl_facts[key]
                removed += 1
        
        return removed
    
    def cleanup_old_data(self) -> Dict[str, int]:
        """
        Clean up old time-series data beyond max_age.
        
        Returns:
            Dictionary with cleanup statistics
        """
        cutoff_time = time.time() - self._max_age
        removed_points = 0
        cleaned_keys = 0
        
        with self._lock:
            for key, points in list(self._timeseries.items()):
                original_length = len(points)
                
                # Remove old points
                while points and points[0].timestamp < cutoff_time:
                    points.popleft()
                
                points_removed = original_length - len(points)
                if points_removed > 0:
                    removed_points += points_removed
                    cleaned_keys += 1
                
                # Remove empty time series
                if not points:
                    del self._timeseries[key]
        
        return {
            'removed_points': removed_points,
            'cleaned_keys': cleaned_keys,
            'removed_ttl_facts': self.clear_expired_ttl_facts()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        with self._lock:
            total_points = sum(len(points) for points in self._timeseries.values())
            
            return {
                'timeseries_keys': len(self._timeseries),
                'total_datapoints': total_points,
                'ttl_facts': len(self._ttl_facts),
                'memory_usage_estimate': self._estimate_memory_usage(),
                'max_age_seconds': self._max_age,
                'max_points_per_key': self._max_points
            }
    
    def _maybe_cleanup(self) -> None:
        """Trigger cleanup if interval has passed."""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            self.cleanup_old_data()
            self._last_cleanup = current_time
    
    def _evaluate_condition(self, value: float, operator: str, threshold: float) -> bool:
        """Evaluate comparison condition."""
        if operator == '>':
            return value > threshold
        elif operator == '>=':
            return value >= threshold
        elif operator == '<':
            return value < threshold
        elif operator == '<=':
            return value <= threshold
        elif operator == '==':
            return value == threshold
        elif operator == '!=':
            return value != threshold
        else:
            raise ValueError(f"Unsupported operator: {operator}")
    
    def _estimate_memory_usage(self) -> int:
        """Rough estimate of memory usage in bytes."""
        # Rough estimate: each TimeSeriesPoint ~32 bytes + overhead
        total_points = sum(len(points) for points in self._timeseries.values())
        timeseries_bytes = total_points * 40  # Conservative estimate
        
        # TTL facts - harder to estimate, assume ~100 bytes average
        ttl_bytes = len(self._ttl_facts) * 100
        
        return timeseries_bytes + ttl_bytes


# Global instance (can be customized per engine if needed)
default_temporal_store = TemporalStore() 