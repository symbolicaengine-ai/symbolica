#!/usr/bin/env python3
"""
Basic Rules Example
==================

This example demonstrates the fundamental concepts of Symbolica:
- Loading rules from YAML
- Creating facts
- Executing rules and getting results
- Understanding rule priorities and conditions
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from symbolica import Engine, facts

def main():
    print("Basic Rules Example")
    print("=" * 50)
    
    # Load rules from YAML file
    engine = Engine.from_yaml("customer_approval.yaml")
    
    print("Loaded rules:")
    for rule in engine.rules:
        print(f"  - {rule.id}: {rule.condition}")
    
    # Test case 1: VIP customer
    print("\nTest 1: VIP Customer")
    vip_customer = facts(
        customer_tier="vip",
        credit_score=800,
        annual_income=120000,
        previous_defaults=0
    )
    
    result = engine.reason(vip_customer)
    print(f"Input: {dict(vip_customer)}")
    print(f"Result: {result.verdict}")
    print(f"Fired rules: {result.fired_rules}")
    print(f"Execution time: {result.execution_time_ms:.2f}ms")
    print(f"Reasoning: {result.reasoning}")
    
    # Test case 2: Regular customer
    print("\nTest 2: Regular Customer")
    regular_customer = facts(
        customer_tier="standard",
        credit_score=680,
        annual_income=60000,
        previous_defaults=0
    )
    
    result = engine.reason(regular_customer)
    print(f"Input: {dict(regular_customer)}")
    print(f"Result: {result.verdict}")
    print(f"Fired rules: {result.fired_rules}")
    print(f"Reasoning: {result.reasoning}")
    
    # Test case 3: High risk customer
    print("\nTest 3: High Risk Customer")
    risky_customer = facts(
        customer_tier="standard",
        credit_score=550,
        annual_income=40000,
        previous_defaults=2
    )
    
    result = engine.reason(risky_customer)
    print(f"Input: {dict(risky_customer)}")
    print(f"Result: {result.verdict}")
    print(f"Fired rules: {result.fired_rules}")
    print(f"Reasoning: {result.reasoning}")
    
    # Test edge case: Conflicting conditions
    print("\nTest 4: Edge Case - VIP with High Risk")
    edge_case = facts(
        customer_tier="vip",
        credit_score=780,
        annual_income=100000,
        previous_defaults=1  # Has defaults but good credit
    )
    
    result = engine.reason(edge_case)
    print(f"Input: {dict(edge_case)}")
    print(f"Result: {result.verdict}")
    print(f"Fired rules: {result.fired_rules}")
    print(f"Reasoning: {result.reasoning}")
    print("Note: VIP rule has higher priority (100) than high_risk rule (75)")

if __name__ == "__main__":
    main() 