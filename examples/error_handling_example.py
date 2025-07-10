#!/usr/bin/env python3
"""
Symbolica Error Handling and Logging Example
============================================

Demonstrates the improved error handling capabilities including:
- Structured logging with context
- Specific exception types with rich context
- Error recovery and graceful degradation
- Comprehensive error reporting
"""

import logging
import tempfile
import os
from pathlib import Path

from symbolica import Engine, Facts
from symbolica.core.exceptions import (
    ValidationError, EvaluationError, FunctionError, 
    DAGError, configure_symbolica_logging, ErrorCollector
)


def setup_logging_demo():
    """Configure logging for demonstration."""
    # Configure Symbolica logging with INFO level for detailed output
    configure_symbolica_logging(level='INFO', 
                               format_string='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    print("✓ Logging configured for detailed error reporting")


def validation_error_demo():
    """Demonstrate validation error handling."""
    print("\n=== Validation Error Handling ===")
    
    # Test invalid YAML structure
    invalid_yaml = """
rules:
  - id: broken_rule
    # Missing condition field
    actions:
      result: "fail"
"""
    
    try:
        engine = Engine.from_yaml(invalid_yaml)
    except ValidationError as e:
        print(f"✓ Caught validation error: {e}")
        print(f"  Error context: {e.context}")
        print(f"  Timestamp: {e.timestamp}")
    
    # Test duplicate rule IDs
    duplicate_rules_yaml = """
rules:
  - id: "rule1"
    condition: "user_type == 'premium'"
    actions:
      access: "granted"
  - id: "rule1"  # Duplicate ID!
    condition: "user_type == 'basic'"
    actions:
      access: "limited"
"""
    
    try:
        engine = Engine.from_yaml(duplicate_rules_yaml)
    except ValidationError as e:
        print(f"✓ Caught duplicate ID error: {e}")
        print(f"  Field: {e.field}")
    

def evaluation_error_demo():
    """Demonstrate evaluation error handling with context."""
    print("\n=== Evaluation Error Handling ===")
    
    # Create engine with problematic rule
    yaml_content = """
rules:
  - id: "syntax_error_rule"
    condition: "invalid syntax here !"
    actions:
      result: "fail"
  
  - id: "division_by_zero_rule"
    condition: "score / 0 > 10"
    actions:
      result: "impossible"
      
  - id: "valid_rule"
    condition: "user_active == true"
    actions:
      result: "success"
"""
    
    try:
        engine = Engine.from_yaml(yaml_content)
        facts = Facts({"user_active": True, "score": 100})
        
        # This will trigger evaluation errors but continue execution
        result = engine.reason(facts)
        
        print(f"✓ Engine continued execution despite errors")
        print(f"  Rules fired: {len(result.fired_rules)}")
        print(f"  Final verdict: {result.verdict}")
        
        # Show which rules had issues
        for rule_id in result.fired_rules:
            reasoning = next((r for r in result.reasoning if r.startswith(rule_id)), "")
            if "error" in reasoning.lower():
                print(f"  Error in {rule_id}: {reasoning}")
                
    except Exception as e:
        print(f"Unexpected error: {e}")


def function_error_demo():
    """Demonstrate custom function error handling."""
    print("\n=== Function Error Handling ===")
    
    yaml_content = """
rules:
  - id: "custom_function_rule"
    condition: "risky_function(user_data) > 0"
    actions:
      result: "processed"
"""
    
    engine = Engine.from_yaml(yaml_content)
    
    # Register a function that might fail
    def risky_function(data):
        if data is None:
            raise ValueError("Data cannot be None")
        if isinstance(data, str) and data == "crash":
            raise RuntimeError("Simulated crash")
        return len(str(data))
    
    engine.register_function("risky_function", risky_function, allow_unsafe=True)
    
    # Test with different data types
    test_cases = [
        {"user_data": "valid"},     # Should work
        {"user_data": None},        # Should cause ValueError
        {"user_data": "crash"},     # Should cause RuntimeError
        {"user_data": 12345},       # Should work
    ]
    
    for i, facts_data in enumerate(test_cases):
        print(f"\n  Test case {i+1}: {facts_data}")
        try:
            facts = Facts(facts_data)
            result = engine.reason(facts)
            print(f"    Result: {result.verdict}")
            if result.reasoning:
                print(f"    Reasoning: {result.reasoning[-1]}")
        except Exception as e:
            print(f"    Error: {e}")


def dag_error_demo():
    """Demonstrate DAG dependency error handling."""
    print("\n=== DAG Dependency Error Handling ===")
    
    # Create rules with circular dependencies
    circular_yaml = """
rules:
  - id: "rule_a"
    condition: "flag_b == true"
    priority: 10
    actions:
      flag_a: true
      
  - id: "rule_b" 
    condition: "flag_a == true"
    priority: 10
    actions:
      flag_b: true
      
  - id: "rule_c"
    condition: "flag_a == true and flag_b == true"
    priority: 5
    actions:
      result: "both_flags_set"
"""
    
    try:
        engine = Engine.from_yaml(circular_yaml)
        facts = Facts({"initial": True})
        
        # This should handle circular dependencies gracefully
        result = engine.reason(facts)
        
        print(f"✓ DAG handled circular dependencies")
        print(f"  Rules fired: {len(result.fired_rules)}")
        print(f"  Execution time: {result.execution_time_ms:.2f}ms")
        
    except Exception as e:
        print(f"DAG error: {e}")


def error_collector_demo():
    """Demonstrate error collection for batch operations."""
    print("\n=== Error Collector for Batch Operations ===")
    
    collector = ErrorCollector()
    
    # Simulate batch validation
    test_rules = [
        {"id": "", "condition": "valid", "actions": {"result": "ok"}},  # Invalid: empty ID
        {"id": "valid1", "condition": "", "actions": {"result": "ok"}},  # Invalid: empty condition
        {"id": "valid2", "condition": "x > 0", "actions": {}},           # Invalid: empty actions
        {"id": "valid3", "condition": "y > 0", "actions": {"result": "ok"}},  # Valid
    ]
    
    for i, rule_data in enumerate(test_rules):
        try:
            # Simulate rule validation
            if not rule_data.get("id"):
                raise ValidationError("Rule ID cannot be empty", rule_id=f"rule_{i}")
            if not rule_data.get("condition"):
                raise ValidationError("Condition cannot be empty", rule_id=rule_data["id"])
            if not rule_data.get("actions"):
                raise ValidationError("Actions cannot be empty", rule_id=rule_data["id"])
                
            collector.add_warning(f"Rule {rule_data['id']} validated successfully")
            
        except ValidationError as e:
            collector.add_error(e)
    
    # Get summary
    summary = collector.get_summary()
    print(f"✓ Batch validation completed:")
    print(f"  Errors: {summary['error_count']}")
    print(f"  Warnings: {summary['warning_count']}")
    
    # Print detailed errors
    for error_dict in summary['errors']:
        print(f"  - {error_dict['error_type']}: {error_dict['message']}")
    
    # This would raise if we had errors
    try:
        collector.raise_if_errors("Batch validation failed")
    except Exception as e:
        print(f"  Batch error summary: {e}")


def configuration_error_demo():
    """Demonstrate configuration error handling."""
    print("\n=== Configuration Error Handling ===")
    
    try:
        # Test with invalid execution config
        engine = Engine(
            rules=[],
            execution_config={
                'max_iterations': 'invalid',  # Should be int
                'unknown_param': 'value'      # Unknown parameter
            }
        )
        
    except Exception as e:
        print(f"Configuration error: {e}")
    
    try:
        # Test with invalid temporal config
        engine = Engine(
            rules=[],
            temporal_config={
                'max_age_seconds': -1,  # Invalid value
            }
        )
        
    except Exception as e:
        print(f"Temporal config error: {e}")


def comprehensive_error_reporting():
    """Demonstrate comprehensive error reporting."""
    print("\n=== Comprehensive Error Reporting ===")
    
    # Create a complex scenario with multiple potential issues
    complex_yaml = """
rules:
  - id: "complex_rule"
    condition: "process_data(user_input, config_value) and score > threshold"
    priority: 10
    actions:
      processed: true
      score: "score * multiplier"
      
  - id: "dependent_rule"
    condition: "processed == true and final_check(score)"
    priority: 5
    actions:
      result: "success"
"""
    
    engine = Engine.from_yaml(complex_yaml)
    
    # Register custom functions that might fail
    def process_data(input_data, config):
        if input_data is None:
            raise ValueError("Input data cannot be None")
        if config == "error":
            raise RuntimeError("Configuration error")
        return len(str(input_data)) > 0
    
    def final_check(value):
        return value is not None and value > 0
    
    engine.register_function("process_data", process_data, allow_unsafe=True)
    engine.register_function("final_check", final_check, allow_unsafe=True)
    
    # Test with various scenarios
    test_scenarios = [
        {
            "name": "Valid scenario",
            "facts": {"user_input": "hello", "config_value": "ok", "score": 10, "threshold": 5, "multiplier": 2}
        },
        {
            "name": "Missing required fact",
            "facts": {"user_input": "hello", "score": 10, "threshold": 5}  # Missing config_value
        },
        {
            "name": "Function error scenario", 
            "facts": {"user_input": None, "config_value": "ok", "score": 10, "threshold": 5}
        },
        {
            "name": "Configuration error",
            "facts": {"user_input": "hello", "config_value": "error", "score": 10, "threshold": 5}
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n  Scenario: {scenario['name']}")
        try:
            facts = Facts(scenario['facts'])
            result = engine.reason(facts)
            
            print(f"    Verdict: {result.verdict}")
            print(f"    Rules fired: {len(result.fired_rules)}")
            print(f"    Execution time: {result.execution_time_ms:.2f}ms")
            
            # Show any error messages in reasoning
            for reasoning in result.reasoning:
                if "error" in reasoning.lower():
                    print(f"    Error: {reasoning}")
                    
        except Exception as e:
            print(f"    Exception: {e}")
            if hasattr(e, 'context'):
                print(f"    Context: {e.context}")


def main():
    """Run all error handling demonstrations."""
    print("🔧 Symbolica Error Handling and Logging Demo")
    print("=" * 50)
    
    setup_logging_demo()
    validation_error_demo()
    evaluation_error_demo()
    function_error_demo()
    dag_error_demo()
    error_collector_demo()
    configuration_error_demo()
    comprehensive_error_reporting()
    
    print("\n" + "=" * 50)
    print("✅ Error handling demonstration completed!")
    print("\nKey improvements demonstrated:")
    print("• Structured logging with context information")
    print("• Specific exception types for different error categories")
    print("• Graceful error recovery and continued execution")
    print("• Rich error context for debugging")
    print("• Error aggregation for batch operations")
    print("• Comprehensive error reporting")


if __name__ == "__main__":
    main() 