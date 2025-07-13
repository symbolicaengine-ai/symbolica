#!/usr/bin/env python3
"""
Temporal Functions Example
==========================

This example demonstrates time-series monitoring with Symbolica:
- Storing time-series data points
- Using temporal functions in rule conditions
- Monitoring trends and sustained conditions
- Building alerting systems
"""

import sys
import os
import time
import random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from symbolica import Engine, facts

def main():
    print("Temporal Functions Example")
    print("=" * 50)
    
    # Load monitoring rules
    engine = Engine.from_file("monitoring.yaml")
    
    print("Infrastructure monitoring rules loaded")
    print("Available temporal functions:")
    print("  - sustained_above(key, threshold, duration)")
    print("  - recent_avg(key, duration)")
    print("  - recent_max(key, duration)")
    print("  - recent_count(key, duration)")
    
    # Simulate normal operation
    print("\nSimulating normal system operation...")
    simulate_normal_load(engine)
    result = engine.reason(facts())
    print(f"Normal operation - Alerts: {len(result.fired_rules)}")
    if result.fired_rules:
        print(f"Fired rules: {result.fired_rules}")
        print(f"Reasoning: {result.reasoning}")
    
    # Simulate CPU spike
    print("\nSimulating CPU spike...")
    simulate_cpu_spike(engine)
    result = engine.reason(facts())
    print(f"CPU spike - Fired rules: {result.fired_rules}")
    if result.verdict:
        print(f"Alerts: {result.verdict}")
        print(f"Reasoning: {result.reasoning}")
    
    # Simulate sustained high CPU
    print("\nSimulating sustained high CPU...")
    simulate_sustained_cpu(engine)
    result = engine.reason(facts())
    print(f"Sustained CPU - Fired rules: {result.fired_rules}")
    if result.verdict:
        print(f"Alerts: {result.verdict}")
        print(f"Reasoning: {result.reasoning}")
    
    # Simulate memory trend
    print("\nSimulating memory usage trend...")
    simulate_memory_trend(engine)
    result = engine.reason(facts())
    print(f"Memory trend - Fired rules: {result.fired_rules}")
    if result.verdict:
        print(f"Alerts: {result.verdict}")
        print(f"Reasoning: {result.reasoning}")
    
    # Simulate network errors
    print("\nSimulating network error burst...")
    simulate_network_errors(engine)
    result = engine.reason(facts())
    print(f"Network errors - Fired rules: {result.fired_rules}")
    if result.verdict:
        print(f"Alerts: {result.verdict}")
        print(f"Reasoning: {result.reasoning}")
    
    # Simulate system overload
    print("\nSimulating system overload...")
    simulate_system_overload(engine)
    result = engine.reason(facts())
    print(f"System overload - Fired rules: {result.fired_rules}")
    if result.verdict:
        print(f"Critical alerts: {result.verdict}")
        print(f"Reasoning: {result.reasoning}")
    
    # Show data analysis
    print("\nData Analysis:")
    analyze_stored_data(engine)

def simulate_normal_load(engine):
    """Simulate normal system operation."""
    for _ in range(30):
        engine.store_datapoint("cpu_usage", random.uniform(20, 40))
        engine.store_datapoint("memory_usage", random.uniform(30, 50))
        engine.store_datapoint("response_time", random.uniform(100, 300))

def simulate_cpu_spike(engine):
    """Simulate a CPU spike."""
    # Normal load first
    for _ in range(10):
        engine.store_datapoint("cpu_usage", random.uniform(20, 40))
    
    # Spike
    for _ in range(5):
        engine.store_datapoint("cpu_usage", random.uniform(96, 99))

def simulate_sustained_cpu(engine):
    """Simulate sustained high CPU usage."""
    # Store high CPU for more than 5 minutes (300 seconds)
    for _ in range(20):  # 20 data points over time
        engine.store_datapoint("cpu_usage", random.uniform(87, 92))

def simulate_memory_trend(engine):
    """Simulate increasing memory usage trend."""
    # Lower usage 10 minutes ago
    for i in range(20):
        base_memory = 60 + (i * 2)  # Increasing trend
        engine.store_datapoint("memory_usage", base_memory + random.uniform(-5, 5))

def simulate_network_errors(engine):
    """Simulate network error burst."""
    # Normal errors
    for _ in range(10):
        if random.random() < 0.1:  # 10% chance of error
            engine.store_datapoint("network_errors", 1)
    
    # Error burst
    for _ in range(60):  # 60 errors in short time
        engine.store_datapoint("network_errors", 1)

def simulate_system_overload(engine):
    """Simulate system-wide performance issues."""
    for _ in range(15):
        engine.store_datapoint("cpu_usage", random.uniform(82, 88))
        engine.store_datapoint("memory_usage", random.uniform(87, 92))
        engine.store_datapoint("response_time", random.uniform(2500, 4000))

def analyze_stored_data(engine):
    """Analyze the temporal data stored in the engine."""
    # Access the temporal store through the temporal service
    if hasattr(engine, '_temporal_service') and hasattr(engine._temporal_service, '_store'):
        store = engine._temporal_service._store
        print(f"Data points stored:")
        for key in store._timeseries.keys():
            points = store._timeseries[key]
            count = len(points)
            if count > 0:
                recent_values = [dp.value for dp in list(points)[-5:]]
                avg_recent = sum(recent_values) / len(recent_values) if recent_values else 0
                print(f"  - {key}: {count} points, recent avg: {avg_recent:.1f}")
    else:
        print("  No temporal store found")
    
    print("\nTemporal function examples:")
    print("  recent_avg('cpu_usage', 300) - Average CPU in last 5 minutes")
    print("  sustained_above('cpu_usage', 85, 300) - CPU >85% for 5+ minutes")
    print("  recent_count('network_errors', 300) - Error count in last 5 minutes")

if __name__ == "__main__":
    main() 