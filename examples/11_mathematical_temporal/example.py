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


def simulate_temperature_monitoring():
    """
    Simulate a temperature monitoring system with both mathematical
    and temporal analysis capabilities
    """
    print("Symbolica Mathematical & Temporal Functions Example")
    print("=" * 60)
    print()
    
    # Initialize the engine
    engine = Engine.from_file("scientific_analysis.yaml")
    
    print("Loaded mathematical and temporal analysis rules")
    print("Simulating industrial temperature monitoring system")
    print()
    
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
    
    # Simulate temperature readings over time
    temperature_readings = [
        {"current_temp": 22.5, "time_desc": "Normal operating temperature"},
        {"current_temp": 45.8, "time_desc": "Moderate temperature rise"},
        {"current_temp": 78.2, "time_desc": "High temperature - approaching critical"},
        {"current_temp": 88.5, "time_desc": "Critical temperature exceeded"},
        {"current_temp": 35.4, "time_desc": "Temperature cooling down"}
    ]
    
    for i, reading in enumerate(temperature_readings):
        print(f"Reading {i+1}: {reading['time_desc']}")
        print(f"Temperature: {reading['current_temp']}°C")
        
        # Combine configuration with current reading
        data = {**monitoring_config, **reading}
        
        # Execute mathematical and temporal analysis
        temperature_facts = facts(**data)
        result = engine.reason(temperature_facts)
        
        if result and result.verdict:
            print("Analysis Results:")
            print(f"  {result.verdict}")
        
        print()
        
        # Add small delay to simulate real-time monitoring
        if i < len(temperature_readings) - 1:
            time.sleep(0.5)
    
    print("Features Demonstrated:")
    print("- Mathematical expressions: unit conversions, thermal calculations")
    print("- Temporal functions: averaging, trending, sustained conditions")
    print("- Combined analysis: real-time monitoring with historical data")
    print("- Complex conditions: multi-level status determination")


def main():
    simulate_temperature_monitoring()


if __name__ == "__main__":
    main() 