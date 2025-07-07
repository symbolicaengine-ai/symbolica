"""
Caching Implementations
======================

High-performance caching with proper eviction policies.
Fixes the caching issues from the original codebase.
"""

import time
from typing import Dict, Any, Optional, OrderedDict
from threading import RLock
from ..core import Cache, CacheError


class LRUCache(Cache):
    """
    Thread-safe LRU cache implementation.
    
    Features:
    - O(1) get and set operations
    - Proper LRU eviction
    - Thread-safe operations
    - Memory bounds
    """
    
    def __init__(self, max_size: int = 1000):
        if max_size <= 0:
            raise CacheError("Cache size must be positive")
        
        self.max_size = max_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value with LRU update."""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            else:
                self._misses += 1
                return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value with LRU eviction."""
        with self._lock:
            if key in self._cache:
                # Update existing key
                self._cache[key] = value
                self._cache.move_to_end(key)
            else:
                # Add new key
                if len(self._cache) >= self.max_size:
                    # Remove least recently used
                    self._cache.popitem(last=False)
                
                self._cache[key] = value
    
    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)
    
    @property
    def hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': self.hit_rate
            }


class TTLCache(Cache):
    """
    Time-to-live cache with expiration.
    
    Features:
    - TTL-based expiration
    - Lazy cleanup on access
    - Memory bounds
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: float = 300):
        if max_size <= 0:
            raise CacheError("Cache size must be positive")
        if ttl_seconds <= 0:
            raise CacheError("TTL must be positive")
        
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._lock = RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value if not expired."""
        with self._lock:
            if key in self._cache:
                value, expires_at = self._cache[key]
                
                if time.time() < expires_at:
                    return value
                else:
                    # Expired - remove it
                    del self._cache[key]
            
            return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value with TTL."""
        expires_at = time.time() + self.ttl_seconds
        
        with self._lock:
            # Clean up expired entries if cache is full
            if len(self._cache) >= self.max_size:
                self._cleanup_expired()
                
                # If still full after cleanup, remove oldest
                if len(self._cache) >= self.max_size:
                    oldest_key = min(self._cache.keys(), 
                                   key=lambda k: self._cache[k][1])
                    del self._cache[oldest_key]
            
            self._cache[key] = (value, expires_at)
    
    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()
    
    def size(self) -> int:
        """Get current cache size (including expired entries)."""
        with self._lock:
            return len(self._cache)
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        now = time.time()
        expired_keys = [
            key for key, (_, expires_at) in self._cache.items()
            if now >= expires_at
        ]
        for key in expired_keys:
            del self._cache[key]


class NoCache(Cache):
    """
    No-op cache that doesn't store anything.
    Useful for disabling caching.
    """
    
    def get(self, key: str) -> Optional[Any]:
        return None
    
    def set(self, key: str, value: Any) -> None:
        pass
    
    def clear(self) -> None:
        pass
    
    def size(self) -> int:
        return 0


class MultiLevelCache(Cache):
    """
    Multi-level cache with L1 (fast, small) and L2 (larger, slower).
    
    Features:
    - Two-level hierarchy
    - Automatic promotion/demotion
    - Configurable sizes
    """
    
    def __init__(self, l1_size: int = 100, l2_size: int = 1000):
        self.l1_cache = LRUCache(l1_size)
        self.l2_cache = LRUCache(l2_size)
    
    def get(self, key: str) -> Optional[Any]:
        """Get from L1 first, then L2."""
        # Try L1 first
        value = self.l1_cache.get(key)
        if value is not None:
            return value
        
        # Try L2
        value = self.l2_cache.get(key)
        if value is not None:
            # Promote to L1
            self.l1_cache.set(key, value)
            return value
        
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set in both levels."""
        self.l1_cache.set(key, value)
        self.l2_cache.set(key, value)
    
    def clear(self) -> None:
        """Clear both levels."""
        self.l1_cache.clear()
        self.l2_cache.clear()
    
    def size(self) -> int:
        """Get total size."""
        return self.l1_cache.size() + self.l2_cache.size()
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get combined statistics."""
        return {
            'l1': self.l1_cache.stats,
            'l2': self.l2_cache.stats,
            'total_size': self.size()
        }


# Factory functions
def create_cache(cache_type: str = "lru", **kwargs) -> Cache:
    """Create cache of specified type."""
    if cache_type == "lru":
        return LRUCache(**kwargs)
    elif cache_type == "ttl":
        return TTLCache(**kwargs)
    elif cache_type == "none":
        return NoCache()
    elif cache_type == "multilevel":
        return MultiLevelCache(**kwargs)
    else:
        raise CacheError(f"Unknown cache type: {cache_type}")


def create_optimal_cache(expected_size: int) -> Cache:
    """Create optimal cache based on expected size."""
    if expected_size <= 100:
        return LRUCache(max_size=expected_size * 2)
    elif expected_size <= 1000:
        return MultiLevelCache(l1_size=100, l2_size=expected_size * 2)
    else:
        return TTLCache(max_size=expected_size, ttl_seconds=600) 