#!/usr/bin/env python3
"""
Comprehensive Symbolica Example
===============================

Demonstrates advanced features of the simplified Symbolica architecture.
"""

import json
import time
from symbolica import Engine, from_yaml, facts

# Complex business rules for e-commerce platform
ecommerce_rules = """
rules:
  # Customer classification rules
  - id: classify_new_customer
    priority: 10
    condition: order_count == 0
    actions:
      customer_type: new
      welcome_discount: 0.1
    tags: [classification, new_customer]
  
  - id: classify_regular_customer
    priority: 20
    condition: order_count >= 1 and order_count < 10
    actions:
      customer_type: regular
      loyalty_points: 100
    tags: [classification, regular_customer]
  
  - id: classify_vip_customer
    priority: 30
    condition: order_count >= 10 or total_spent > 1000
    actions:
      customer_type: vip
      free_shipping: true
      loyalty_points: 500
    tags: [classification, vip_customer]
  
  # Dynamic pricing rules
  - id: bulk_discount
    priority: 40
    condition: item_count > 5 and customer_type != 'new'
    actions:
      bulk_discount: 0.15
      discount_reason: "Bulk purchase discount"
    tags: [pricing, bulk]
  
  - id: vip_pricing
    priority: 50
    condition: customer_type == 'vip'
    actions:
      vip_discount: 0.2
      priority_support: true
    tags: [pricing, vip]
  
  # Inventory and shipping rules
  - id: expedited_shipping
    priority: 60
    condition: customer_type == 'vip' and order_value > 200
    actions:
      shipping_method: expedited
      shipping_cost: 0
    tags: [shipping, expedited]
  
  - id: free_shipping_threshold
    priority: 70
    condition: order_value > 75 and customer_type != 'new'
    actions:
      shipping_cost: 0
      shipping_reason: "Free shipping on orders over $75"
    tags: [shipping, free]
"""


def demonstrate_simple_explanations():
    """Show simple, clear explanations for LLM integration."""
    print("=== Simple Explanations Demo ===")
    
    engine = Engine.from_yaml(ecommerce_rules)
    
    # Complex customer scenario
    customer_data = facts(
        order_count=12,
        total_spent=1500,
        item_count=7,
        order_value=300
    )
    
    result = engine.reason(customer_data)
    
    print(f"Customer facts: {customer_data.data}")
    print(f"Final verdict: {json.dumps(result.verdict, indent=2)}")
    print(f"Rules fired: {result.fired_rules}")
    print(f"Execution time: {result.execution_time_ms:.2f}ms")
    
    print("\nSimple reasoning:")
    print(result.reasoning)
    
    print("\nLLM-friendly JSON:")
    print(result.get_reasoning_json())


def demonstrate_performance():
    """Show performance characteristics."""
    print("\n=== Performance Demo ===")
    
    engine = Engine.from_yaml(ecommerce_rules)
    
    # Single execution timing
    test_data = facts(order_count=5, total_spent=500, item_count=3, order_value=150)
    result = engine.reason(test_data)
    
    print(f"Single execution: {result.execution_time_ms:.3f}ms")
    print(f"Rules fired: {len(result.fired_rules)}")
    
    # Bulk execution timing
    test_cases = [
        facts(order_count=0, total_spent=0, item_count=1, order_value=50),
        facts(order_count=5, total_spent=300, item_count=3, order_value=100),
        facts(order_count=15, total_spent=2000, item_count=10, order_value=500),
    ]
    
    start_time = time.perf_counter()
    results = []
    for test_case in test_cases:
        for _ in range(100):  # 100 iterations per case
            results.append(engine.reason(test_case))
    
    total_time = time.perf_counter() - start_time
    avg_time = total_time / 300  # 300 total executions
    
    print(f"\nBulk execution (300 runs):")
    print(f"Total time: {total_time*1000:.2f}ms")
    print(f"Average per execution: {avg_time*1000:.3f}ms")
    print(f"Executions per second: {1/avg_time:.0f}")


def demonstrate_llm_integration():
    """Show how to integrate reasoning results into LLM prompts."""
    print("\n=== LLM Integration Demo ===")
    
    engine = Engine.from_yaml(ecommerce_rules)
    
    # Customer service scenario
    customer_facts = facts(
        order_count=3,
        total_spent=450,
        item_count=4,
        order_value=85
    )
    
    result = engine.reason(customer_facts)
    
    # Generate LLM prompt with reasoning context
    prompt = f"""
You are an AI customer service representative for an e-commerce platform.
A customer is contacting support about their order.

CUSTOMER PROFILE:
- Order count: {customer_facts.data['order_count']}
- Total spent: ${customer_facts.data['total_spent']}
- Current order items: {customer_facts.data['item_count']}
- Current order value: ${customer_facts.data['order_value']}

BUSINESS RULES ANALYSIS:
{result.get_reasoning_json()}

Based on this analysis, provide personalized customer service.
Consider their classification and applicable benefits.
"""
    
    print("Generated LLM Prompt Preview:")
    print(prompt[:600] + "..." if len(prompt) > 600 else prompt)


if __name__ == "__main__":
    print("Symbolica Comprehensive Demo")
    print("=" * 50)
    
    demonstrate_simple_explanations()
    demonstrate_performance()
    demonstrate_llm_integration()
    
    print("\n" + "=" * 50)
    print("Demo complete! Key features demonstrated:")
    print("✓ Simple, clear explanations")
    print("✓ Sub-millisecond performance")
    print("✓ LLM-ready reasoning context")
    print("✓ Clean, simplified architecture") 