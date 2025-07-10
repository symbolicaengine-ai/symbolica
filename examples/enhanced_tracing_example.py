#!/usr/bin/env python3
"""
Enhanced Hierarchical Tracing Example
=====================================

Demonstrates the new hierarchical trace generation system that provides
granular condition-level insights for LLM processing and debugging.

New features:
- Hierarchical trace trees showing evaluation flow
- Detailed condition breakdowns for AND/OR/NOT operations
- Function call tracing with arguments and results  
- Field access tracking with missing field handling
- LLM-ready structured reasoning output
- Performance metrics at condition level
"""

import json
from pathlib import Path

from symbolica import Engine, Facts
from symbolica.core.exceptions import configure_symbolica_logging


def setup_demo():
    """Configure logging for detailed trace output."""
    configure_symbolica_logging(level='INFO')
    print("✓ Enhanced tracing configured")


def complex_condition_tracing():
    """Demonstrate hierarchical tracing for complex conditions."""
    print("\n=== Complex Condition Hierarchical Tracing ===")
    
    # Create rules with complex nested conditions
    yaml_content = """
rules:
  - id: "loan_approval"
    condition: "credit_score >= 700 and (income > 50000 or assets > 100000) and not has_bankruptcy"
    priority: 100
    actions:
      loan_approved: true
      approval_reason: "meets_criteria"
      
  - id: "premium_customer"
    condition: "account_age >= 5 and total_deposits > 10000 and len(transaction_history) > 100"
    priority: 90
    actions:
      customer_tier: "premium"
      benefits_eligible: true
      
  - id: "risk_assessment"
    condition: "risk_score(credit_score, income, debt_ratio) < 0.3 and compliance_check(customer_id)"
    priority: 80
    actions:
      risk_level: "low"
      additional_checks: false
"""
    
    engine = Engine.from_yaml(yaml_content)
    
    # Register custom functions for demonstration
    engine.register_function("risk_score", lambda credit, income, debt: (1000 - credit) / 1000 + debt - (income / 100000), allow_unsafe=True)
    engine.register_function("compliance_check", lambda customer_id: customer_id not in ["blocked123", "fraud456"], allow_unsafe=True)
    
    # Test cases with different condition evaluation paths
    test_cases = [
        {
            "name": "Approved via high income",
            "facts": {
                "credit_score": 750,
                "income": 75000,
                "assets": 50000,
                "has_bankruptcy": False,
                "account_age": 6,
                "total_deposits": 15000,
                "transaction_history": ["t1", "t2", "t3"] * 50,  # 150 transactions
                "debt_ratio": 0.2,
                "customer_id": "good_customer"
            }
        },
        {
            "name": "Approved via high assets (low income)",
            "facts": {
                "credit_score": 720,
                "income": 40000,  # Below 50k threshold
                "assets": 150000,  # High assets compensate
                "has_bankruptcy": False,
                "account_age": 3,
                "total_deposits": 5000,
                "transaction_history": ["t1"] * 50,  # Only 50 transactions
                "debt_ratio": 0.15,
                "customer_id": "asset_rich"
            }
        },
        {
            "name": "Rejected due to bankruptcy",
            "facts": {
                "credit_score": 800,
                "income": 100000,
                "assets": 200000,
                "has_bankruptcy": True,  # This will fail the loan
                "account_age": 10,
                "total_deposits": 50000,
                "transaction_history": ["t1"] * 200,
                "debt_ratio": 0.1,
                "customer_id": "bankrupt_customer"
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n--- {test_case['name']} ---")
        facts = Facts(test_case['facts'])
        result = engine.reason(facts)
        
        print(f"Verdict: {result.verdict}")
        print(f"Rules fired: {result.fired_rules}")
        
        # Show hierarchical reasoning
        hierarchical_reasoning = result.get_hierarchical_reasoning()
        print(f"\nHierarchical Reasoning Summary:")
        print(f"- Rules evaluated: {hierarchical_reasoning['execution_summary']['rules_evaluated']}")
        print(f"- Rules fired: {hierarchical_reasoning['execution_summary']['rules_fired']}")
        print(f"- Facts modified: {hierarchical_reasoning['execution_summary']['facts_modified']}")
        print(f"- Total execution time: {hierarchical_reasoning['execution_summary']['total_execution_time_ms']:.2f}ms")
        
        # Show reasoning chain
        reasoning_chain = hierarchical_reasoning.get('reasoning_chain', [])
        for step in reasoning_chain:
            print(f"\nRule '{step['rule_id']}':")
            print(f"  Condition: {step['condition']}")
            print(f"  Result: {step['result']}")
            print(f"  Explanation: {step['explanation']}")
            print(f"  Key factors: {step.get('key_factors', [])}")
            if step.get('execution_time_ms', 0) > 0:
                print(f"  Execution time: {step['execution_time_ms']:.2f}ms")


def boolean_operation_breakdown():
    """Demonstrate detailed breakdown of boolean operations."""
    print("\n=== Boolean Operation Detailed Breakdown ===")
    
    yaml_content = """
rules:
  - id: "complex_and_rule"
    condition: "score >= 80 and active == true and verified == true and balance > 1000"
    actions:
      status: "qualified"
      
  - id: "complex_or_rule"  
    condition: "vip_status == true or total_spent > 10000 or referrals >= 5 or tenure_years >= 10"
    actions:
      rewards_eligible: true
      
  - id: "mixed_logic_rule"
    condition: "(age >= 18 and age <= 65) and (income > 30000 or has_cosigner == true) and not blacklisted"
    actions:
      loan_eligible: true
"""
    
    engine = Engine.from_yaml(yaml_content)
    
    # Test case that will show different evaluation paths
    facts = Facts({
        "score": 85,
        "active": True,
        "verified": False,  # This will cause AND to fail
        "balance": 2000,
        "vip_status": False,
        "total_spent": 5000,
        "referrals": 6,  # This will cause OR to succeed
        "tenure_years": 2,
        "age": 30,
        "income": 25000,  # Below threshold
        "has_cosigner": True,  # But has cosigner
        "blacklisted": False
    })
    
    result = engine.reason(facts)
    print(f"Final verdict: {result.verdict}")
    
    # Get detailed decision path
    decision_path = result.explain_decision_path()
    print(f"\nDetailed Decision Path:")
    print(decision_path)
    
    # Get critical conditions
    critical_conditions = result.get_critical_conditions()
    print(f"\nCritical Conditions:")
    for condition in critical_conditions:
        print(f"Rule '{condition['rule_id']}':")
        print(f"  Condition: {condition['condition']}")
        print(f"  Result: {condition['result']}")
        print(f"  Key factors:")
        for factor in condition['key_factors']:
            print(f"    - {factor}")


def function_call_tracing():
    """Demonstrate function call tracing with arguments and results."""
    print("\n=== Function Call Detailed Tracing ===")
    
    yaml_content = """
rules:
  - id: "data_validation"
    condition: "len(email) > 5 and contains(email, '@') and startswith(phone, '+1') and validate_age(birth_year)"
    actions:
      data_valid: true
      
  - id: "scoring_rule"
    condition: "calculate_score(credit_history, income, debt) >= 0.7"
    actions:
      score_category: "excellent"
"""
    
    engine = Engine.from_yaml(yaml_content)
    
    # Register custom functions with various behaviors
    def validate_age(birth_year):
        current_year = 2024
        age = current_year - birth_year
        return 18 <= age <= 100
    
    def calculate_score(credit_history, income, debt):
        # Complex scoring function
        credit_factor = len(credit_history) / 10.0
        income_factor = min(income / 50000, 1.0)
        debt_factor = max(0, 1.0 - debt / income) if income > 0 else 0
        return (credit_factor + income_factor + debt_factor) / 3.0
    
    engine.register_function("validate_age", validate_age, allow_unsafe=True)
    engine.register_function("calculate_score", calculate_score, allow_unsafe=True)
    
    facts = Facts({
        "email": "user@example.com",
        "phone": "+1-555-1234",
        "birth_year": 1990,
        "credit_history": ["good", "good", "excellent", "good", "excellent"] * 3,  # 15 entries
        "income": 60000,
        "debt": 15000
    })
    
    result = engine.reason(facts)
    print(f"Result: {result.verdict}")
    
    # Show hierarchical reasoning with function details
    hierarchical_reasoning = result.get_hierarchical_reasoning()
    
    print(f"\nFunction Call Analysis:")
    for rule_id, trace_info in hierarchical_reasoning.get('rule_traces', {}).items():
        print(f"\nRule '{rule_id}':")
        print(f"  Condition: {trace_info.get('condition', 'unknown')}")
        print(f"  Result: {trace_info.get('result', False)}")
        print(f"  Explanation: {trace_info.get('explanation', 'No explanation')}")
        
        execution_summary = trace_info.get('execution_summary', {})
        if execution_summary.get('functions_called', 0) > 0:
            print(f"  Functions called: {execution_summary['functions_called']}")
            print(f"  Total evaluation time: {execution_summary.get('total_time_ms', 0):.3f}ms")


def field_access_tracing():
    """Demonstrate field access and missing field handling."""
    print("\n=== Field Access and Missing Field Tracing ===")
    
    yaml_content = """
rules:
  - id: "profile_completeness"
    condition: "name != null and email != null and phone != null and address != null"
    actions:
      profile_complete: true
      
  - id: "optional_fields"
    condition: "bio != null or website != null or social_media != null"
    actions:
      has_optional_info: true
      
  - id: "computed_field"
    condition: "age > 21 and full_name != null"
    actions:
      adult_with_name: true
"""
    
    engine = Engine.from_yaml(yaml_content)
    
    # Test with missing fields
    facts = Facts({
        "name": "John Doe",
        "email": "john@example.com",
        # phone is missing
        "address": "123 Main St",
        # bio, website, social_media all missing
        "age": 25
        # full_name is missing
    })
    
    result = engine.reason(facts)
    print(f"Result: {result.verdict}")
    
    # Show field access details
    hierarchical_reasoning = result.get_hierarchical_reasoning()
    
    print(f"\nField Access Analysis:")
    for rule_id, trace_info in hierarchical_reasoning.get('rule_traces', {}).items():
        print(f"\nRule '{rule_id}':")
        print(f"  Result: {trace_info.get('result', False)}")
        
        field_dependencies = trace_info.get('field_dependencies', [])
        if field_dependencies:
            print(f"  Fields accessed: {field_dependencies}")
            
            # Show which fields were missing
            facts_dict = facts.data
            missing_fields = [field for field in field_dependencies if field not in facts_dict]
            present_fields = [field for field in field_dependencies if field in facts_dict]
            
            if present_fields:
                print(f"  Present fields: {present_fields}")
            if missing_fields:
                print(f"  Missing fields: {missing_fields}")


def llm_ready_output():
    """Demonstrate LLM-ready structured output."""
    print("\n=== LLM-Ready Structured Output ===")
    
    yaml_content = """
rules:
  - id: "customer_segmentation"
    condition: "total_purchases > 1000 and avg_order_value > 50 and last_purchase_days <= 30"
    actions:
      segment: "high_value"
      
  - id: "engagement_level"
    condition: "email_opens >= 5 and clicks >= 2 and shares > 0"
    actions:
      engagement: "highly_engaged"
"""
    
    engine = Engine.from_yaml(yaml_content)
    
    facts = Facts({
        "total_purchases": 1500,
        "avg_order_value": 75,
        "last_purchase_days": 15,
        "email_opens": 8,
        "clicks": 3,
        "shares": 2
    })
    
    result = engine.reason(facts)
    
    # Get LLM-ready output
    simple_context = result.get_llm_context()
    hierarchical_context = result.get_hierarchical_reasoning()
    
    print("Simple LLM Context (backward compatible):")
    print(json.dumps(simple_context, indent=2))
    
    print("\nHierarchical LLM Context (enhanced):")
    print(json.dumps(hierarchical_context, indent=2))
    
    print(f"\nHuman-readable decision path:")
    print(result.explain_decision_path())


def performance_analysis():
    """Demonstrate performance analysis capabilities."""
    print("\n=== Performance Analysis with Hierarchical Tracing ===")
    
    # Create rules with varying complexity
    yaml_content = """
rules:
  - id: "simple_rule"
    condition: "value > 10"
    actions:
      category: "simple"
      
  - id: "complex_rule"
    condition: "calculate_complex_score(data1, data2, data3, data4) >= threshold and validate_all_conditions(status, flags, metadata)"
    actions:
      category: "complex"
      
  - id: "medium_rule"
    condition: "len(items) > 5 and sum(values) > 1000 and all_valid"
    actions:
      category: "medium"
"""
    
    engine = Engine.from_yaml(yaml_content)
    
    # Register functions with different performance characteristics
    def calculate_complex_score(data1, data2, data3, data4):
        # Simulate complex calculation
        import time
        time.sleep(0.001)  # 1ms delay
        return (data1 + data2 * data3 - data4) / 4.0
    
    def validate_all_conditions(status, flags, metadata):
        # Simulate validation
        import time
        time.sleep(0.0005)  # 0.5ms delay
        return status == "active" and len(flags) == 0 and metadata is not None
    
    engine.register_function("calculate_complex_score", calculate_complex_score, allow_unsafe=True)
    engine.register_function("validate_all_conditions", validate_all_conditions, allow_unsafe=True)
    
    facts = Facts({
        "value": 15,
        "data1": 10,
        "data2": 20,
        "data3": 5,
        "data4": 3,
        "threshold": 20,
        "status": "active",
        "flags": [],
        "metadata": {"type": "test"},
        "items": ["a", "b", "c", "d", "e", "f"],
        "values": [100, 200, 300, 400, 500],
        "all_valid": True
    })
    
    result = engine.reason(facts)
    
    # Show performance breakdown
    hierarchical_reasoning = result.get_hierarchical_reasoning()
    
    print(f"Performance Summary:")
    print(f"- Total execution time: {result.execution_time_ms:.3f}ms")
    
    execution_summary = hierarchical_reasoning.get('execution_summary', {})
    print(f"- Rules evaluated: {execution_summary.get('rules_evaluated', 0)}")
    print(f"- Rules fired: {execution_summary.get('rules_fired', 0)}")
    
    print(f"\nPer-rule performance:")
    for step in hierarchical_reasoning.get('reasoning_chain', []):
        rule_id = step.get('rule_id')
        exec_time = step.get('execution_time_ms', 0)
        print(f"- Rule '{rule_id}': {exec_time:.3f}ms")


def main():
    """Run all enhanced tracing demonstrations."""
    print("🔍 Enhanced Hierarchical Tracing Demo")
    print("=" * 50)
    
    setup_demo()
    complex_condition_tracing()
    boolean_operation_breakdown()
    function_call_tracing()
    field_access_tracing()
    llm_ready_output()
    performance_analysis()
    
    print("\n" + "=" * 50)
    print("✅ Enhanced tracing demonstration completed!")
    print("\nKey capabilities demonstrated:")
    print("• Hierarchical condition breakdown (AND/OR/NOT operations)")
    print("• Function call tracing with arguments and results")
    print("• Field access tracking with missing field detection")
    print("• LLM-ready structured reasoning output")
    print("• Performance analysis at condition level")
    print("• Critical path identification")
    print("• Human-readable decision path explanations")
    print("\nThis enhanced tracing enables:")
    print("• Better debugging of complex rule conditions")
    print("• LLM-powered rule analysis and optimization")
    print("• Detailed explainability for AI agent decisions")
    print("• Performance optimization insights")


if __name__ == "__main__":
    main() 