"""
Enhanced Tracing Example
========================

Demonstrates Symbolica's enhanced tracing capabilities for AI explainability.
Shows how to get detailed reasoning explanations suitable for LLM prompt inclusion.
"""

import json
from symbolica import Engine, facts, TraceLevel

# Example rules for customer classification with complex dependencies
CUSTOMER_RULES = '''
rules:
  - id: basic_customer
    priority: 10
    condition: purchase_amount > 0
    actions:
      customer_type: basic
      eligible_for_support: true
    tags: [classification, basic]
    
  - id: premium_customer  
    priority: 20
    condition: purchase_amount > 1000 and customer_type == 'basic'
    actions:
      customer_type: premium
      discount_rate: 0.1
      priority_support: true
    tags: [classification, premium]
    
  - id: vip_customer
    priority: 30
    condition: purchase_amount > 5000 and customer_type == 'premium'
    actions:
      customer_type: vip
      discount_rate: 0.2
      personal_manager: true
    tags: [classification, vip]
    
  - id: loyalty_bonus
    priority: 40
    condition: customer_type == 'vip' and years_active > 3
    actions:
      loyalty_bonus: 500
      special_offers: true
    tags: [rewards, loyalty]
    
  - id: fraud_check
    priority: 100
    condition: purchase_amount > 10000 and customer_type == 'basic'
    actions:
      requires_verification: true
      hold_order: true
    tags: [security, fraud]
'''

def demonstrate_basic_tracing():
    """Show basic tracing functionality."""
    print("=== Basic Tracing Demo ===")
    
    # Create engine with detailed tracing
    engine = Engine.from_yaml(CUSTOMER_RULES, trace_level=TraceLevel.DETAILED)
    
    # Test case: Premium customer
    customer_facts = facts(
        purchase_amount=1500,
        years_active=2
    )
    
    result = engine.reason(customer_facts)
    
    print(f"Final verdict: {result.verdict}")
    print(f"Rules that fired: {result.fired_rules}")
    print(f"Execution time: {result.execution_time_ms:.2f}ms")
    print()
    
    # Show detailed explanation
    print("Detailed reasoning:")
    print(result.explain_reasoning())
    print()


def demonstrate_llm_context():
    """Show LLM-friendly context generation."""
    print("=== LLM Context Demo ===")
    
    engine = Engine.from_yaml(CUSTOMER_RULES)
    
    # Test case: VIP customer with loyalty bonus
    vip_facts = facts(
        purchase_amount=6000,
        years_active=5
    )
    
    result = engine.reason(vip_facts)
    
    # Get structured context for LLM
    llm_context = result.get_llm_context()
    
    print("LLM Context (JSON):")
    print(json.dumps(llm_context, indent=2))
    print()


def demonstrate_rule_traces():
    """Show detailed rule-by-rule tracing."""
    print("=== Rule-by-Rule Tracing Demo ===")
    
    engine = Engine.from_yaml(CUSTOMER_RULES)
    
    # Test case: Large purchase (potential fraud)
    large_purchase_facts = facts(
        purchase_amount=15000,
        years_active=1
    )
    
    result = engine.reason(large_purchase_facts)
    
    print("Individual Rule Traces:")
    for rule_trace in result.rule_traces:
        print(f"\n--- Rule: {rule_trace.rule_id} ---")
        print(f"Priority: {rule_trace.priority}")
        print(f"Fired: {rule_trace.fired}")
        print(f"Condition: {rule_trace.condition_trace.expression}")
        print(f"Explanation: {rule_trace.explain()}")
        
        if rule_trace.condition_trace.field_accesses:
            print("Fields accessed:")
            for fa in rule_trace.condition_trace.field_accesses:
                print(f"  - {fa.field_name}: {fa.value} ({fa.access_type})")
        
        if rule_trace.fired and rule_trace.actions_applied:
            print(f"Actions applied: {rule_trace.actions_applied}")
    
    print()


def demonstrate_reasoning_chain():
    """Show step-by-step reasoning chain."""
    print("=== Reasoning Chain Demo ===")
    
    engine = Engine.from_yaml(CUSTOMER_RULES)
    
    # Test case: Customer progression through tiers
    progression_facts = facts(
        purchase_amount=7500,
        years_active=4
    )
    
    result = engine.reason(progression_facts)
    
    print("Step-by-step reasoning chain:")
    for i, rule_trace in enumerate(result.rule_traces):
        if rule_trace.fired:
            print(f"\nStep {i+1}: {rule_trace.rule_id}")
            print(f"  Condition: {rule_trace.condition_trace.expression}")
            
            # Show field values at time of evaluation
            field_values = {fa.field_name: fa.value for fa in rule_trace.condition_trace.field_accesses}
            print(f"  Field values: {field_values}")
            
            print(f"  Result: {rule_trace.condition_trace.result}")
            print(f"  Actions: {rule_trace.actions_applied}")
            print(f"  Reasoning: {rule_trace.explain()}")
    
    print(f"\nFinal state: {result.verdict}")
    print()


def demonstrate_error_tracing():
    """Show error tracing capabilities."""
    print("=== Error Tracing Demo ===")
    
    # Create rules with potential errors
    error_rules = '''
    rules:
      - id: safe_rule
        condition: amount > 0
        actions:
          status: valid
      
      - id: risky_rule
        condition: invalid_field == 'test'
        actions:
          status: risky
    '''
    
    engine = Engine.from_yaml(error_rules)
    
    # Test with missing field
    test_facts = facts(amount=100)
    
    result = engine.reason(test_facts)
    
    print("Error tracing:")
    for rule_trace in result.rule_traces:
        if rule_trace.condition_trace.error:
            print(f"Rule {rule_trace.rule_id} had error:")
            print(f"  Error: {rule_trace.condition_trace.error}")
            print(f"  Expression: {rule_trace.condition_trace.expression}")
        else:
            print(f"Rule {rule_trace.rule_id}: {rule_trace.explain()}")
    
    print()


def demonstrate_prompt_integration():
    """Show how to integrate reasoning into LLM prompts."""
    print("=== LLM Prompt Integration Demo ===")
    
    engine = Engine.from_yaml(CUSTOMER_RULES)
    
    # Simulate AI agent decision making
    customer_data = facts(
        purchase_amount=2500,
        years_active=3
    )
    
    result = engine.reason(customer_data)
    
    # Create a prompt that includes reasoning
    prompt = f"""
You are an AI customer service agent. A customer has made a purchase and you need to 
provide appropriate service based on their classification.

Customer Purchase: $2,500
Years Active: 3 years

REASONING ENGINE ANALYSIS:
{result.get_reasoning_json()}

Based on this deterministic analysis, provide personalized customer service recommendations.
Focus on the customer's tier status and applicable benefits.
"""
    
    print("Generated LLM Prompt:")
    print(prompt)
    print()


if __name__ == "__main__":
    print("Symbolica Enhanced Tracing Demo")
    print("=" * 40)
    print()
    
    demonstrate_basic_tracing()
    # demonstrate_llm_context()
    # demonstrate_rule_traces()
    # demonstrate_reasoning_chain()
    # demonstrate_error_tracing()
    # demonstrate_prompt_integration()
    
    print("Demo complete! The engine provides comprehensive tracing for AI explainability.") 