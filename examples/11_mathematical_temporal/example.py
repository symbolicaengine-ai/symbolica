#!/usr/bin/env python3
"""
Mathematical and Temporal Functions Example

This example demonstrates Symbolica's mathematical calculation capabilities
and temporal functions through a real-world temperature monitoring system.

Features showcased:
- Mathematical expressions: complex calculations, unit conversions
- Temporal functions: recent_avg(), recent_max(), recent_min(), sustained_above(), sustained_below()
- Combined analysis: mathematical calculations using temporal data
- Real-time monitoring: trend detection and alert systems

Run this example to see how mathematical and temporal functions work together
for advanced system monitoring and analysis.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import time
from symbolica import Engine, facts


def test_mathematical_calculations():
    """Test mathematical calculation capabilities"""
    print("Mathematical Calculations Demo")
    print("=" * 40)
    
    # Initialize the engine with mathematical rules
    engine = Engine.from_file("scientific_analysis.yaml")
    
    # System configuration for thermal analysis
    monitoring_config = {
        "sensor_id": "TEMP_001",
        "reference_temp": 20.0,  # Reference temperature (°C)
        "critical_temp": 85.0,   # Critical high temperature
        "min_safe_temp": 10.0,   # Minimum safe temperature
        "stability_threshold": 5.0,  # Maximum acceptable temperature variation
        
        # Material properties for thermal calculations
        "expansion_coefficient": 0.000012,  # Linear expansion coefficient
        "original_length": 2.5,  # meters
        "material_mass": 50.0,   # kg
        "specific_heat": 450.0,  # J/(kg·K) - steel
        "material_stress_coefficient": 1.2
    }
    
    # Test different temperature scenarios
    test_scenarios = [
        {"temp": 22.5, "desc": "Normal operating temperature"},
        {"temp": 78.2, "desc": "High temperature - approaching critical"},
        {"temp": 88.5, "desc": "Critical temperature exceeded"},
        {"temp": 5.0, "desc": "Below minimum safe temperature"}
    ]
    
    for scenario in test_scenarios:
        print(f"\n{scenario['desc']}")
        print(f"Temperature: {scenario['temp']}°C")
        
        # Combine configuration with current reading
        data = {**monitoring_config, "current_temp": scenario['temp']}
        result = engine.reason(facts(**data))
        
        if result and result.verdict:
            print(f"  Fahrenheit: {result.verdict.get('temp_fahrenheit', 'N/A'):.1f}°F")
            print(f"  Kelvin: {result.verdict.get('temp_kelvin', 'N/A'):.1f}K")
            print(f"  System Status: {result.verdict.get('system_status', 'UNKNOWN')}")
            print(f"  Alert Level: {result.verdict.get('alert_level', 0)}")
            print(f"  Thermal Expansion: {result.verdict.get('thermal_expansion', 0):.6f}m")
            print(f"  Heat Energy: {result.verdict.get('heat_capacity_joules', 0):,.0f}J")
            print(f"  Thermal Stress: {result.verdict.get('thermal_stress_factor', 0):.1f}")


def test_temporal_functions():
    """Test temporal function capabilities"""
    print("\n\nTemporal Functions Demo")
    print("=" * 40)
    
    # Initialize engine with temporal rules  
    engine = Engine.from_file("scientific_monitoring.yaml")
    
    # Add temporal data to the engine's store
    print("Adding temperature readings to temporal store...")
    
    # Simulate historical temperature data for manufacturing process
    temperature_data = [
        25.2, 25.8, 26.1, 25.9, 26.3, 27.1, 26.8, 25.7, 25.4, 26.0,
        26.5, 27.2, 26.9, 25.8, 26.1, 26.4, 25.9, 26.7, 26.3, 25.6,
        26.0, 26.8, 27.0, 26.2, 25.9, 26.5, 26.1, 25.8, 26.3, 26.6, 25.7
    ]
    
    # Add data to temporal store
    for temp in temperature_data:
        engine.store_datapoint("process_temperature", temp)
    
    print(f"Added {len(temperature_data)} temperature readings")
    
    # Test manufacturing quality control
    print("\nManufacturing Quality Control Analysis:")
    qc_data = facts(
        target_temperature=26.0,
        tolerance=1.5
    )
    
    result = engine.reason(qc_data)
    if result and result.verdict:
        print(f"  Average Temperature: {result.verdict.get('qc_avg_temperature', 'N/A'):.1f}°C")
        print(f"  Temperature Range: {result.verdict.get('qc_temperature_range', 'N/A'):.1f}°C")
        print(f"  Process Stability: {result.verdict.get('qc_temperature_stability', 'N/A'):.1f}%")
        print(f"  Deviation from Target: {result.verdict.get('qc_deviation_from_target', 'N/A'):.1f}°C")
        print(f"  Within Tolerance: {result.verdict.get('qc_within_tolerance', 'N/A')}")
        print(f"  QC Status: {result.verdict.get('qc_status', 'UNKNOWN')}")
        print(f"  Yield Estimate: {result.verdict.get('qc_yield_estimate', 0)}%")
    
    # Test trend analysis
    print("\nTemperature Trend Analysis:")
    result = engine.reason(facts())
    if result and result.verdict:
        print(f"  Short-term Average: {result.verdict.get('trend_short_term', 'N/A'):.1f}°C")
        print(f"  Long-term Average: {result.verdict.get('trend_long_term', 'N/A'):.1f}°C")
        print(f"  Trend Direction: {result.verdict.get('trend_direction', 'UNKNOWN')}")
        print(f"  Trend Rate: {result.verdict.get('trend_rate', 'N/A'):.2f}")
        print(f"  Temperature Prediction: {result.verdict.get('trend_prediction', 'N/A'):.1f}°C")


def main():
    print("Symbolica Mathematical & Temporal Functions Example")
    print("=" * 60)
    
    # Test mathematical capabilities
    test_mathematical_calculations()
    
    # Test temporal capabilities  
    test_temporal_functions()
    
    print("\n" + "=" * 60)
    print("Features Demonstrated:")
    print("✓ Mathematical expressions: unit conversions, thermal calculations")
    print("✓ Temporal functions: recent_avg(), recent_max(), recent_min()")
    print("✓ Temporal analysis: trend detection and process monitoring")
    print("✓ Combined analysis: mathematical calculations using temporal data")
    print("✓ Real-time monitoring: quality control and alert systems")


if __name__ == "__main__":
    main() 