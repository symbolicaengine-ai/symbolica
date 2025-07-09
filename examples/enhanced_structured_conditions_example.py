#!/usr/bin/env python3
"""
Enhanced Structured Conditions Example
======================================

Demonstrates the flexible new rule syntax with nested structured conditions.
"""

from symbolica import Engine, facts

# Example showing the new flexible structured condition syntax
enhanced_rules_yaml = """
rules:
  - id: "insurance_claim_processing"
    priority: 100
    if:
      all:
        - "state == 'TX'"
        - "days_since_incident <= 60"
        - "policy_max_reporting_days == 30"  # older contracts
      any:
        - "incident_date == null"
        - "report_date == null"
    then:
      high_value: true
      review_required: true
    tags: ["insurance", "complex"]
  
  - id: "loan_approval_complex"
    priority: 90
    if:
      all:
        - "age >= 18"
        - "income > 50000"
        - any:
          - "credit_score >= 750"
          - all:
            - "credit_score >= 650"
            - "employment_years >= 2" 
            - "debt_to_income_ratio < 0.4"
        - not:
            any:
              - "bankruptcy_history == true"
              - "criminal_record == true"
    then:
      approved: true
      interest_rate: 3.5
      loan_amount: 500000
    tags: ["loan", "approval", "complex"]

  - id: "vip_customer_identification"
    priority: 80
    if:
      any:
        - all:
          - "annual_spending > 100000"
          - "account_age_years >= 5"
        - all:
          - "net_worth > 1000000"
          - "referral_count >= 3"
        - "executive_level == 'C-Suite'"
    then:
      vip_status: true
      concierge_service: true
      priority_support: true
    tags: ["vip", "customer"]

  - id: "fraud_detection_advanced"
    priority: 200  # High priority for security
    if:
      any:
        - all:
          - "transaction_amount > 10000"
          - "transaction_country not in ['US', 'CA', 'UK']"
          - "unusual_hour == true"
        - all:
          - "velocity_check_failed == true"
          - "device_fingerprint_mismatch == true"
        - "merchant_risk_score > 0.8"
    then:
      flagged_for_fraud: true
      hold_transaction: true
      notify_security: true
    tags: ["fraud", "security", "high-priority"]
"""

def demo_enhanced_structured_conditions():
    """Demonstrate enhanced structured condition processing."""
    print("=== Enhanced Structured Conditions Demo ===")
    
    engine = Engine.from_yaml(enhanced_rules_yaml)
    
    # Test Case 1: Insurance claim processing
    print("\n1. Insurance Claim Processing:")
    insurance_facts = facts(
        state="TX",
        days_since_incident=45,
        policy_max_reporting_days=30,
        incident_date=None,  # null/None triggers any condition
        report_date="2024-01-15"
    )
    
    result1 = engine.reason(insurance_facts)
    print(f"Facts: {insurance_facts.data}")
    print(f"Rules fired: {result1.fired_rules}")
    print(f"Verdict: {result1.verdict}")
    print(f"Reasoning: {result1.reasoning}")
    
    # Test Case 2: Complex loan approval 
    print("\n2. Complex Loan Approval:")
    loan_facts = facts(
        age=35,
        income=85000,
        credit_score=720,
        employment_years=3,
        debt_to_income_ratio=0.3,
        bankruptcy_history=False,
        criminal_record=False
    )
    
    result2 = engine.reason(loan_facts)
    print(f"Facts: {loan_facts.data}")
    print(f"Rules fired: {result2.fired_rules}")
    print(f"Verdict: {result2.verdict}")
    print(f"Reasoning: {result2.reasoning}")
    
    # Test Case 3: VIP customer identification
    print("\n3. VIP Customer Identification:")
    vip_facts = facts(
        annual_spending=150000,
        account_age_years=7,
        net_worth=500000,
        referral_count=1,
        executive_level="Director"
    )
    
    result3 = engine.reason(vip_facts)
    print(f"Facts: {vip_facts.data}")
    print(f"Rules fired: {result3.fired_rules}")
    print(f"Verdict: {result3.verdict}")
    print(f"Reasoning: {result3.reasoning}")
    
    # Test Case 4: Fraud detection
    print("\n4. Advanced Fraud Detection:")
    fraud_facts = facts(
        transaction_amount=15000,
        transaction_country="RO",  # Romania - not in safe list
        unusual_hour=True,
        velocity_check_failed=False,
        device_fingerprint_mismatch=False,
        merchant_risk_score=0.4
    )
    
    result4 = engine.reason(fraud_facts)
    print(f"Facts: {fraud_facts.data}")
    print(f"Rules fired: {result4.fired_rules}")
    print(f"Verdict: {result4.verdict}")
    print(f"Reasoning: {result4.reasoning}")

def demo_syntax_comparison():
    """Show comparison between old and new syntax."""
    print("\n=== Syntax Comparison ===")
    
    # Old simple syntax
    old_syntax = """
rules:
  - id: "simple_approval"
    if: "credit_score > 700 and income > 50000 and not bankruptcy_history"
    then:
      approved: true
"""
    
    # New structured syntax - equivalent logic
    new_syntax = """
rules:
  - id: "structured_approval"
    if:
      all:
        - "credit_score > 700"
        - "income > 50000"
        - not: "bankruptcy_history"
    then:
      approved: true
"""
    
    engine_old = Engine.from_yaml(old_syntax)
    engine_new = Engine.from_yaml(new_syntax)
    
    test_facts = facts(credit_score=750, income=75000, bankruptcy_history=False)
    
    result_old = engine_old.reason(test_facts)
    result_new = engine_new.reason(test_facts)
    
    print("Old syntax reasoning:", result_old.reasoning)
    print("New syntax reasoning:", result_new.reasoning)
    print("Both produce same result:", result_old.verdict == result_new.verdict)

def demo_complex_nesting():
    """Demonstrate deep nesting capabilities."""
    print("\n=== Complex Nesting Demo ===")
    
    deep_nesting_yaml = """
rules:
  - id: "deep_nested_rule"
    priority: 100
    if:
      all:
        - "base_eligible == true"
        - any:
          - "fast_track_qualified == true"
          - all:
            - "standard_track_eligible == true"
            - any:
              - "priority_customer == true"
              - all:
                - "regular_customer == true"
                - "waiting_time_acceptable == true"
                - not:
                    any:
                      - "system_overloaded == true"
                      - "maintenance_window == true"
    then:
      process_request: true
      estimated_time: "2-4 hours"
    tags: ["complex", "nested"]
"""
    
    engine = Engine.from_yaml(deep_nesting_yaml)
    
    # Test case that should traverse the deep nesting
    complex_facts = facts(
        base_eligible=True,
        fast_track_qualified=False,
        standard_track_eligible=True,
        priority_customer=False,
        regular_customer=True,
        waiting_time_acceptable=True,
        system_overloaded=False,
        maintenance_window=False
    )
    
    result = engine.reason(complex_facts)
    print(f"Deep nested condition result: {result.verdict}")
    print(f"Reasoning: {result.reasoning}")

if __name__ == "__main__":
    print("Enhanced Structured Conditions Demonstration")
    print("=" * 50)
    
    demo_enhanced_structured_conditions()
    demo_syntax_comparison()
    demo_complex_nesting()
    
    print("\n=== Demo Complete ===")
    print("Enhanced features demonstrated:")
    print("✅ Complex nested all/any/not conditions")
    print("✅ Multiple levels of nesting")
    print("✅ Backwards compatibility with simple string conditions")
    print("✅ Clear reasoning explanations for complex logic")
    print("✅ Real-world use cases (insurance, loans, fraud, VIP)") 