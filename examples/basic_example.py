#!/usr/bin/env python3
"""
Basic Symbolica Example
=======================

Demonstrates the clean new architecture for AI agents.
"""

import json
from symbolica import Engine, from_yaml, facts

# Example 1: Simple customer approval rules
customer_rules = """
rules:
  - id: "vip_customer"
    priority: 100
    condition: "customer_tier == 'vip' and credit_score > 750"
    actions:
      approved: true
      credit_limit: 50000
      message: "VIP customer approved with high limit"
    tags: ["vip", "approval"]
  
  - id: "regular_customer"
    priority: 50
    condition: "credit_score > 650 and annual_income > 50000"
    actions:
      approved: true
      credit_limit: 25000
      message: "Regular customer approved"
    tags: ["regular", "approval"]
  
  - id: "high_risk"
    priority: 75
    condition: "previous_defaults > 0 or credit_score < 600"
    actions:
      approved: false
      message: "Application rejected due to high risk"
    tags: ["risk", "rejection"]
"""

def demo_customer_approval():
    """Demonstrate customer approval logic."""
    print("=== Customer Approval Demo ===")
    
    # Create engine from YAML
    engine = from_yaml(customer_rules)
    
    # Test cases
    test_cases = [
        {
            "name": "VIP Customer",
            "facts": {
                "customer_tier": "vip",
                "credit_score": 800,
                "annual_income": 120000,
                "previous_defaults": 0
            }
        },
        {
            "name": "Regular Customer",
            "facts": {
                "customer_tier": "regular",
                "credit_score": 700,
                "annual_income": 65000,
                "previous_defaults": 0
            }
        },
        {
            "name": "High Risk Customer",
            "facts": {
                "customer_tier": "regular",
                "credit_score": 550,
                "annual_income": 40000,
                "previous_defaults": 1
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print(f"Facts: {test_case['facts']}")
        
        # Run inference with simple explanation
        result = engine.reason(facts(**test_case['facts']))
        
        print(f"Verdict: {json.dumps(result.verdict, indent=2)}")
        print(f"Rules fired: {result.fired_rules}")
        print(f"Execution time: {result.execution_time_ms:.2f}ms")
        
        # Show simple reasoning
        print("Reasoning:")
        print(result.reasoning)
        
        # Show clean LLM context
        print("LLM Context:", list(result.get_llm_context().keys()))
        
        print("-" * 50)


# def demo_dynamic_rules():
#     """Demonstrate dynamic rule creation."""
#     print("\n=== Dynamic Rule Creation Demo ===")
    
#     from symbolica import create_simple_rule, Engine
    
#     # Create rules programmatically
#     rules = [
#         create_simple_rule(
#             "temperature_check",
#             "temperature > 30",
#             alert_level="high",
#             action="turn_on_ac"
#         ),
#         create_simple_rule(
#             "humidity_check", 
#             "humidity > 80",
#             alert_level="medium",
#             action="turn_on_dehumidifier"
#         ),
#         create_simple_rule(
#             "comfort_check",
#             "temperature > 25 and humidity < 60",
#             comfort_level="optimal",
#             action="maintain_current"
#         )
#     ]
    
#     # Create engine from rules
#     engine = Engine.from_rules(rules)
    
#     # Test environmental conditions
#     conditions = [
#         {"temperature": 35, "humidity": 45},
#         {"temperature": 28, "humidity": 85},
#         {"temperature": 26, "humidity": 55},
#     ]
    
#     for condition in conditions:
#         result = engine.reason(condition)
#         print(f"Conditions: {condition}")
#         print(f"Actions: {result.verdict}")
#         print(f"Execution time: {result.execution_time_ms:.2f}ms")
#         print("-" * 30)


# def demo_condition_testing():
#     """Demonstrate condition testing for debugging."""
#     print("\n=== Condition Testing Demo ===")
    
#     engine = from_yaml(customer_rules)
    
#     # Test various conditions
#     test_facts = {
#         "customer_tier": "vip",
#         "credit_score": 800,
#         "annual_income": 120000,
#         "previous_defaults": 0
#     }
    
#     conditions_to_test = [
#         "customer_tier == 'vip'",
#         "credit_score > 750",
#         "customer_tier == 'vip' and credit_score > 750",
#         "previous_defaults > 0",
#         "annual_income > 100000"
#     ]
    
#     print(f"Testing conditions against facts: {test_facts}")
#     for condition in conditions_to_test:
#         result = engine.test_condition(condition, test_facts)
#         print(f"'{condition}' -> {result}")


# def demo_performance():
#     """Demonstrate performance characteristics."""
#     print("\n=== Performance Demo ===")
#     import time
    
#     engine = from_yaml(customer_rules)
    
#     # Single execution
#     facts = {"customer_tier": "vip", "credit_score": 800, "annual_income": 120000}
#     result = engine.reason(facts)
#     print(f"Single execution: {result.execution_time_ms:.2f}ms")
    
#     # Multiple executions (cache should help)
#     start_time = time.perf_counter()
#     for _ in range(1000):
#         engine.reason(facts)
#     bulk_time = time.perf_counter() - start_time
    
#     print(f"1000 executions: {bulk_time*1000:.2f}ms total")
#     print(f"Average per execution: {bulk_time:.4f}ms")
#     print(f"Rules per second: {1000/bulk_time:.0f}")


# def demo_error_handling():
#     """Demonstrate clean error handling."""
#     print("\n=== Error Handling Demo ===")
    
#     from symbolica import ValidationError, ExecutionError
    
#     try:
#         # Invalid YAML
#         engine = from_yaml("invalid: yaml: content:")
#     except Exception as e:
#         print(f"Invalid YAML error: {type(e).__name__}: {e}")
    
#     try:
#         # Missing required fields
#         engine = from_yaml("""
#         rules:
#           - condition: "x > 5"
#             # Missing id and actions
#         """)
#     except Exception as e:
#         print(f"Validation error: {type(e).__name__}: {e}")
    
#     try:
#         # Invalid condition syntax
#         engine = from_yaml("""
#         rules:
#           - id: "test"
#             condition: "x >>>> invalid"
#             then:
#               result: true
#         """)
#         engine.reason({"x": 10})
#     except Exception as e:
#         print(f"Execution error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    print("Symbolica Clean Architecture Demo")
    print("=" * 40)
    
    demo_customer_approval()
    # demo_dynamic_rules()  # Skip this for now - needs Engine.from_rules
    #demo_condition_testing()
    #demo_performance()
    # demo_error_handling()  # Skip this for now
    
    print("\n=== Demo Complete ===")
    print("The new architecture provides:")
    print("✓ Clean, simple APIs")
    print("✓ Fast execution (sub-millisecond)")
    print("✓ Proper error handling")
    print("✓ Content-based caching")
    print("✓ Immutable data structures")
    print("✓ Easy debugging and tracing") 