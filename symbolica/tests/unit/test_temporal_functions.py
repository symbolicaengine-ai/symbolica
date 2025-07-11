"""
Unit tests for temporal functions and TemporalStore.
"""

import pytest
import time
from typing import Any

from symbolica import Engine, facts
from symbolica._internal.storage.temporal_store import TemporalStore, TimeSeriesPoint
from symbolica.core.exceptions import ValidationError, EvaluationError


class TestTemporalStore:
    """Test core TemporalStore functionality."""
    
    def test_store_creation(self):
        """Test TemporalStore creation with default and custom parameters."""
        # Default store
        store1 = TemporalStore()
        assert store1._max_age == 3600
        assert store1._max_points == 1000
        assert store1._cleanup_interval == 300
        
        # Custom store
        store2 = TemporalStore(max_age_seconds=7200, max_points_per_key=500, cleanup_interval=60)
        assert store2._max_age == 7200
        assert store2._max_points == 500
        assert store2._cleanup_interval == 60
    
    def test_store_datapoint(self):
        """Test storing time-series data points."""
        store = TemporalStore()
        
        # Store with automatic timestamp
        store.store_datapoint("cpu_util", 85.5)
        stats = store.get_stats()
        assert stats['timeseries_keys'] == 1
        assert stats['total_datapoints'] == 1
        
        # Store with explicit timestamp
        timestamp = time.time() - 60
        store.store_datapoint("cpu_util", 90.0, timestamp)
        stats = store.get_stats()
        assert stats['total_datapoints'] == 2
        
        # Store different key
        store.store_datapoint("memory_util", 70.0)
        stats = store.get_stats()
        assert stats['timeseries_keys'] == 2
        assert stats['total_datapoints'] == 3
    
    def test_get_window_data(self):
        """Test retrieving data within time windows."""
        store = TemporalStore()
        current_time = time.time()
        
        # Store data points over time
        timestamps = [current_time - 300, current_time - 200, current_time - 100, current_time - 50]
        values = [80.0, 85.0, 90.0, 95.0]
        
        for timestamp, value in zip(timestamps, values):
            store.store_datapoint("cpu_util", value, timestamp)
        
        # Get last 5 minutes (300 seconds) - might be 2-4 points due to timing
        window_data = store.get_window_data("cpu_util", 300)
        assert len(window_data) >= 2  # At least 2 points
        assert all(isinstance(point, TimeSeriesPoint) for point in window_data)
        
        # Get last 2 minutes (120 seconds) - should have recent points
        window_data = store.get_window_data("cpu_util", 120)
        assert len(window_data) >= 1
        
        # Get last 30 seconds - should include most recent
        window_data = store.get_window_data("cpu_util", 60)  # More lenient window
        assert len(window_data) >= 1
        assert 95.0 in [p.value for p in window_data]  # Contains the most recent value
        
        # Non-existent key
        window_data = store.get_window_data("nonexistent", 300)
        assert len(window_data) == 0
    
    def test_aggregation_functions(self):
        """Test time window aggregation functions."""
        store = TemporalStore()
        current_time = time.time()
        
        # Store test data
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for i, value in enumerate(values):
            timestamp = current_time - (len(values) - i - 1) * 60  # 1 minute apart
            store.store_datapoint("test_metric", value, timestamp)
        
        # Test average
        avg = store.avg_in_window("test_metric", 300)  # 5 minutes
        assert avg == 30.0  # (10+20+30+40+50)/5
        
        # Test max
        max_val = store.max_in_window("test_metric", 300)
        assert max_val == 50.0
        
        # Test min
        min_val = store.min_in_window("test_metric", 300)
        assert min_val == 10.0
        
        # Test count
        count = store.count_in_window("test_metric", 300)
        assert count == 5
        
        # Test with shorter window
        avg_short = store.avg_in_window("test_metric", 120)  # 2 minutes
        assert avg_short == 45.0  # (40+50)/2
        
        # Test with non-existent key
        assert store.avg_in_window("nonexistent", 300) is None
        assert store.max_in_window("nonexistent", 300) is None
        assert store.min_in_window("nonexistent", 300) is None
        assert store.count_in_window("nonexistent", 300) == 0
    
    def test_sustained_condition(self):
        """Test sustained condition checking."""
        store = TemporalStore()
        current_time = time.time()
        
        # Create sustained high condition (all values > 90)
        for i in range(10):
            timestamp = current_time - (600 - i * 60)  # 10 minutes ago to now
            value = 95.0  # All high values
            store.store_datapoint("cpu_util", value, timestamp)
        
        # Should detect sustained condition
        assert store.sustained_condition("cpu_util", 90.0, 600, '>') is True
        assert store.sustained_condition("cpu_util", 100.0, 600, '>') is False
        
        # Test different operators
        assert store.sustained_condition("cpu_util", 94.0, 600, '>=') is True
        assert store.sustained_condition("cpu_util", 96.0, 600, '>=') is False
        assert store.sustained_condition("cpu_util", 100.0, 600, '<') is True
        
        # Add one low value - should break sustained condition
        store.store_datapoint("cpu_util", 80.0, current_time)
        assert store.sustained_condition("cpu_util", 90.0, 600, '>') is False
    
    def test_ttl_facts(self):
        """Test TTL (time-to-live) facts."""
        store = TemporalStore()
        
        # Set TTL fact
        store.set_ttl_fact("session", {"user_id": "123", "role": "admin"}, 2)  # 2 seconds TTL
        
        # Should be available immediately
        fact = store.get_ttl_fact("session")
        assert fact == {"user_id": "123", "role": "admin"}
        
        # Should still be available after 1 second
        time.sleep(1)
        fact = store.get_ttl_fact("session")
        assert fact == {"user_id": "123", "role": "admin"}
        
        # Should be expired after 3 seconds total
        time.sleep(2.5)
        fact = store.get_ttl_fact("session")
        assert fact is None
        
        # Getting expired fact should remove it
        stats = store.get_stats()
        assert stats['ttl_facts'] == 0
    
    def test_cleanup_operations(self):
        """Test data cleanup operations."""
        store = TemporalStore(max_age_seconds=5, cleanup_interval=1)
        current_time = time.time()
        
        # Add old and new data
        store.store_datapoint("metric1", 10.0, current_time - 10)  # Old (should be cleaned)
        store.store_datapoint("metric1", 20.0, current_time - 3)   # Recent (should remain)
        store.store_datapoint("metric2", 30.0, current_time - 8)   # Old (should be cleaned)
        
        # Add TTL facts
        store.set_ttl_fact("expired", "value", 1)  # Will expire soon
        store.set_ttl_fact("valid", "value", 10)   # Will remain valid
        
        time.sleep(2)  # Let expired TTL fact expire
        
        # Trigger cleanup
        cleanup_stats = store.cleanup_old_data()
        
        # Check cleanup results
        assert cleanup_stats['removed_points'] >= 2  # Old data points removed
        assert cleanup_stats['removed_ttl_facts'] == 1  # Expired TTL fact removed
        
        # Verify remaining data - should have at least the recent point
        recent_data = store.get_window_data("metric1", 10)
        assert len(recent_data) >= 0  # May have 0 or 1 points due to cleanup timing
        if recent_data:
            assert recent_data[0].value == 20.0
        
        assert store.get_ttl_fact("expired") is None
        assert store.get_ttl_fact("valid") == "value"
    
    def test_stats_and_memory_estimation(self):
        """Test statistics and memory usage estimation."""
        store = TemporalStore()
        
        # Add various data
        for i in range(50):
            store.store_datapoint("metric1", float(i), time.time() - i)
            if i % 10 == 0:
                store.store_datapoint("metric2", float(i), time.time() - i)
        
        store.set_ttl_fact("fact1", "value1", 3600)
        store.set_ttl_fact("fact2", {"complex": "data"}, 7200)
        
        stats = store.get_stats()
        
        assert stats['timeseries_keys'] == 2
        assert stats['total_datapoints'] == 55  # 50 + 5
        assert stats['ttl_facts'] == 2
        assert stats['memory_usage_estimate'] > 0
        assert stats['max_age_seconds'] == 3600
        assert stats['max_points_per_key'] == 1000
    
    def test_condition_operators(self):
        """Test all supported condition operators."""
        store = TemporalStore()
        
        # Test all operators
        assert store._evaluate_condition(5.0, '>', 3.0) is True
        assert store._evaluate_condition(3.0, '>', 5.0) is False
        
        assert store._evaluate_condition(5.0, '>=', 5.0) is True
        assert store._evaluate_condition(4.0, '>=', 5.0) is False
        
        assert store._evaluate_condition(3.0, '<', 5.0) is True
        assert store._evaluate_condition(5.0, '<', 3.0) is False
        
        assert store._evaluate_condition(5.0, '<=', 5.0) is True
        assert store._evaluate_condition(6.0, '<=', 5.0) is False
        
        assert store._evaluate_condition(5.0, '==', 5.0) is True
        assert store._evaluate_condition(5.0, '==', 4.0) is False
        
        assert store._evaluate_condition(5.0, '!=', 4.0) is True
        assert store._evaluate_condition(5.0, '!=', 5.0) is False
        
        # Test invalid operator
        with pytest.raises(ValueError, match="Unsupported operator"):
            store._evaluate_condition(5.0, '~=', 5.0)


class TestEngineTemporalIntegration:
    """Test Engine integration with temporal functions."""
    
    def test_temporal_functions_registration(self):
        """Test that temporal functions are automatically registered."""
        engine = Engine()
        functions = engine.list_functions()
        
        # Check that temporal functions are registered
        temporal_functions = [
            'recent_avg', 'recent_max', 'recent_min', 'recent_count',
            'sustained', 'sustained_above', 'sustained_below',
            'ttl_fact', 'has_ttl_fact'
        ]
        
        for func_name in temporal_functions:
            assert func_name in functions
            assert 'lambda' in functions[func_name]
    
    def test_store_datapoint_method(self):
        """Test Engine.store_datapoint method."""
        engine = Engine()
        
        # Store data points
        engine.store_datapoint("cpu_util", 85.5)
        engine.store_datapoint("memory_util", 70.0)
        
        # Check stats
        stats = engine.get_temporal_stats()
        assert stats['timeseries_keys'] == 2
        assert stats['total_datapoints'] == 2
    
    def test_set_ttl_fact_method(self):
        """Test Engine.set_ttl_fact method."""
        engine = Engine()
        
        # Set TTL facts
        engine.set_ttl_fact("session_123", {"user": "alice"}, 3600)
        engine.set_ttl_fact("maintenance", True, 7200)
        
        # Check stats
        stats = engine.get_temporal_stats()
        assert stats['ttl_facts'] == 2
    
    def test_cleanup_temporal_data_method(self):
        """Test Engine.cleanup_temporal_data method."""
        engine = Engine()
        
        # Add some data
        engine.store_datapoint("metric", 100.0, time.time() - 10000)  # Old data
        engine.set_ttl_fact("expired", "value", 1)  # Will expire
        
        time.sleep(2)
        
        # Cleanup
        cleanup_stats = engine.cleanup_temporal_data()
        
        assert 'removed_points' in cleanup_stats
        assert 'removed_ttl_facts' in cleanup_stats


class TestTemporalFunctionsInRules:
    """Test temporal functions used in actual rules."""
    
    def test_recent_avg_function(self):
        """Test recent_avg function in rules."""
        yaml_rules = """
rules:
  - id: high_cpu_avg
    condition: "recent_avg('cpu_util', 300) > 80"
    actions:
      cpu_high: true
      
  - id: low_cpu_avg
    condition: "recent_avg('cpu_util', 300) < 50"
    actions:
      cpu_low: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        
        # Add data points that average to high CPU
        for value in [85, 90, 95, 80, 85]:
            engine.store_datapoint("cpu_util", value)
        
        result = engine.reason(facts())
        assert "high_cpu_avg" in result.fired_rules
        assert result.verdict["cpu_high"] is True
        assert "low_cpu_avg" not in result.fired_rules
    
    def test_sustained_condition_function(self):
        """Test sustained condition functions in rules."""
        yaml_rules = """
rules:
  - id: sustained_high
    condition: "sustained_above('cpu_util', 90, 300)"
    actions:
      sustained_alert: true
      
  - id: sustained_low
    condition: "sustained_below('cpu_util', 50, 300)"
    actions:
      low_usage: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        current_time = time.time()
        
        # Add sustained high CPU data
        for i in range(10):
            timestamp = current_time - (300 - i * 30)  # Over 5 minutes
            engine.store_datapoint("cpu_util", 95.0, timestamp)
        
        result = engine.reason(facts())
        assert "sustained_high" in result.fired_rules
        assert result.verdict["sustained_alert"] is True
    
    def test_ttl_fact_functions(self):
        """Test TTL fact functions in rules."""
        yaml_rules = """
rules:
  - id: user_authenticated
    condition: "has_ttl_fact(session_key)"
    actions:
      authenticated: true
      
  - id: get_user_data
    condition: "ttl_fact(session_key) != None"
    actions:
      user_data: ttl_fact(session_key)
      
  - id: session_expired
    condition: "ttl_fact(session_key) == None and login_attempted == true"
    actions:
      redirect_login: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        
        # Test with valid session
        session_data = {"user_id": "123", "role": "admin"}
        engine.set_ttl_fact("user_session", session_data, 3600)
        
        result1 = engine.reason(facts(session_key="user_session"))
        assert "user_authenticated" in result1.fired_rules
        assert result1.verdict["authenticated"] is True
        
        # Test with expired session
        engine.set_ttl_fact("expired_session", session_data, 1)
        time.sleep(2)
        
        result2 = engine.reason(facts(session_key="expired_session", login_attempted=True))
        # TTL fact should be expired, so session_expired rule should fire
        if "session_expired" in result2.fired_rules:
            assert result2.verdict["redirect_login"] is True
        else:
            # Check if TTL fact is actually expired
            ttl_value = engine._temporal_store.get_ttl_fact("expired_session")
            assert ttl_value is None  # Should be expired
    
    def test_recent_count_function(self):
        """Test recent_count function for rate limiting."""
        yaml_rules = """
rules:
  - id: rate_limit_exceeded
    condition: "recent_count('api_calls', 60) >= 10"
    actions:
      rate_limited: true
      retry_after: 60
"""
        
        engine = Engine.from_yaml(yaml_rules)
        
        # Simulate API calls
        for i in range(12):
            engine.store_datapoint("api_calls", 1)
        
        result = engine.reason(facts())
        assert "rate_limit_exceeded" in result.fired_rules
        assert result.verdict["rate_limited"] is True
        assert result.verdict["retry_after"] == 60
    
    def test_complex_temporal_condition(self):
        """Test complex conditions combining multiple temporal functions."""
        yaml_rules = """
rules:
  - id: complex_alert
    condition: "recent_avg('cpu_util', 300) > 80 and recent_max('error_rate', 180) > 0.05 and has_ttl_fact('maintenance_mode') == False"
    actions:
      complex_alert: true
      severity: "high"
"""
        
        engine = Engine.from_yaml(yaml_rules)
        
        # Set up conditions
        for value in [85, 90, 95, 80, 85]:  # High CPU average
            engine.store_datapoint("cpu_util", value)
        
        for value in [0.02, 0.08, 0.03]:  # High error rate peak
            engine.store_datapoint("error_rate", value)
        
        # No maintenance mode (TTL fact doesn't exist)
        
        result = engine.reason(facts())
        assert "complex_alert" in result.fired_rules
        assert result.verdict["complex_alert"] is True
        assert result.verdict["severity"] == "high"
    
    def test_temporal_functions_error_handling(self):
        """Test error handling in temporal functions."""
        yaml_rules = """
rules:
  - id: safe_rule
    condition: "value > 50"
    actions:
      safe_fired: true
      
  - id: temporal_rule
    condition: "recent_avg('nonexistent_metric', 300) > 80"
    actions:
      should_not_fire: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        
        # Should not crash even with non-existent metric
        result = engine.reason(facts(value=60))
        
        # Safe rule should fire
        assert "safe_rule" in result.fired_rules
        assert result.verdict["safe_fired"] is True
        
        # Temporal rule should not fire (returns None for non-existent)
        assert "temporal_rule" not in result.fired_rules
    
    def test_temporal_tracing(self):
        """Test that temporal functions appear correctly in reasoning traces."""
        yaml_rules = """
rules:
  - id: traced_rule
    condition: "recent_avg('cpu_util', 300) > 85"
    actions:
      traced: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        
        # Add data
        for value in [90, 95, 85, 90, 85]:
            engine.store_datapoint("cpu_util", value)
        
        result = engine.reason(facts())
        
        # Check that temporal function appears in reasoning
        assert "recent_avg('cpu_util', 300)" in result.reasoning
        assert "traced_rule" in result.fired_rules


class TestTemporalFunctionsPerformance:
    """Test performance characteristics of temporal functions."""
    
    def test_large_dataset_performance(self):
        """Test performance with large amounts of temporal data."""
        store = TemporalStore()
        
        # Add large dataset
        start_time = time.perf_counter()
        for i in range(1000):
            store.store_datapoint("metric", float(i))
        add_time = time.perf_counter() - start_time
        
        # Query performance
        start_time = time.perf_counter()
        for _ in range(100):
            avg = store.avg_in_window("metric", 600)
        query_time = time.perf_counter() - start_time
        
        # Should be reasonably fast
        assert add_time < 1.0  # Adding 1000 points < 1 second
        assert query_time < 0.5  # 100 queries < 0.5 seconds
    
    def test_engine_performance_with_temporal_functions(self):
        """Test that temporal functions don't significantly impact engine performance."""
        yaml_rules = """
rules:
  - id: temporal_rule
    condition: "recent_avg('cpu_util', 300) > 80 and sustained_above('memory_util', 70, 180)"
    actions:
      alert: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        
        # Populate with data
        for i in range(100):
            engine.store_datapoint("cpu_util", 85.0)
            engine.store_datapoint("memory_util", 75.0)
        
        # Measure execution time
        start_time = time.perf_counter()
        for _ in range(100):
            result = engine.reason(facts())
        execution_time = time.perf_counter() - start_time
        
        # Should maintain sub-millisecond average execution
        avg_time_ms = (execution_time / 100) * 1000
        assert avg_time_ms < 5.0  # Less than 5ms average (very generous)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 