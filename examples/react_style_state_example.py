#!/usr/bin/env python3
"""
React-Style State Management Example
====================================

Demonstrates how Symbolica enables React-style state management where rules can 
write intermediate facts that other rules immediately use, creating sophisticated 
multi-stage computational pipelines.

This example shows:
1. Stage 1: Risk Assessment - Calculates intermediate metrics
2. Stage 2: Customer Segmentation - Uses risk metrics to determine tier  
3. Stage 3: Pricing & Approval - Uses both risk and tier for final decisions
4. Stage 4: Audit Trail - Tracks decision factors

Like React's useState and useEffect, facts flow between rules in a predictable manner.
"""

from symbolica import Engine, facts
import time


def main():
    # Define rules with facts (intermediate state) and actions (final outputs)
    yaml_rules = """
    rules:
      # Stage 1: Risk Assessment - Compute intermediate metrics
      - id: "risk_assessment"
        priority: 100
        condition: "True"  # Always runs first
        facts:
          # Financial health metrics
          debt_ratio: monthly_debt / monthly_income
          credit_utilization: current_debt / credit_limit
          income_stability: employment_years / 10
          
          # Composite risk score (0.0 = best, 1.0 = worst)
          financial_risk: (debt_ratio * 0.4) + (credit_utilization * 0.3) + ((1 - income_stability) * 0.3)
          
          # Risk categories for downstream rules
          is_low_risk: financial_risk < 0.2
          is_medium_risk: financial_risk >= 0.2 and financial_risk < 0.5
          is_high_risk: financial_risk >= 0.5
        actions:
          risk_assessment_complete: True
      
      # Stage 2: Customer Segmentation - Use risk metrics to determine tier
      - id: "premium_tier_qualification"
        priority: 90
        condition: "is_low_risk and annual_income > 80000 and credit_score > 750"
        facts:
          customer_tier: "premium"
          base_rate: 0.025
          max_credit_multiplier: 6
        actions:
          tier_assigned: "premium"
      
      - id: "standard_tier_qualification"  
        priority: 89
        condition: "is_medium_risk and annual_income > 40000 and credit_score > 650"
        facts:
          customer_tier: "standard"
          base_rate: 0.045
          max_credit_multiplier: 4
        actions:
          tier_assigned: "standard"
      
      - id: "basic_tier_qualification"
        priority: 88
        condition: "not is_high_risk and annual_income > 25000"
        facts:
          customer_tier: "basic"
          base_rate: 0.065
          max_credit_multiplier: 2
        actions:
          tier_assigned: "basic"
      
      # Stage 3: Pricing & Approval - Use both risk and tier for decisions
      - id: "calculate_pricing"
        priority: 80
        condition: "customer_tier is not None and base_rate is not None"
        facts:
          # Dynamic pricing based on risk and tier
          risk_premium: financial_risk * 0.02
          final_rate: base_rate + risk_premium
          
          # Credit limit calculation
          max_credit_limit: annual_income * max_credit_multiplier
          
          # Approval logic
          meets_approval_criteria: final_rate < 0.10 and max_credit_limit >= 10000
        actions:
          pricing_calculated: True
      
      - id: "approve_application"
        priority: 70
        condition: "meets_approval_criteria"
        facts:
          approval_reason: customer_tier + "_tier_approved"
        actions:
          approved: True
          interest_rate: final_rate
          credit_limit: max_credit_limit
          
      - id: "decline_application"
        priority: 69
        condition: "not meets_approval_criteria"
        facts:
          decline_reason: "high_risk_or_low_income"
        actions:
          approved: False
          decline_code: "RISK_INCOME"
      
      # Stage 4: Audit Trail - Track decision factors for explainability
      - id: "create_audit_trail"
        priority: 60
        condition: "True"  # Always create audit trail
        actions:
          audit_summary: customer_tier + "_customer_processed"
          risk_score_rounded: round(financial_risk, 4)
          final_rate_rounded: round(final_rate, 4)
    """
    
    # Create engine and test with different customer profiles
    engine = Engine.from_yaml(yaml_rules)
    
    print("🎯 React-Style State Management in Symbolica")
    print("=" * 50)
    print()
    
    # Test Case 1: Premium Customer
    print("Test Case 1: Premium Customer Profile")
    print("-" * 40)
    
    premium_customer = facts(
        monthly_debt=1200,
        monthly_income=8000,
        current_debt=15000,
        credit_limit=25000,
        employment_years=8,
        annual_income=96000,
        credit_score=780
    )
    
    start_time = time.perf_counter()
    result1 = engine.reason(premium_customer)
    execution_time = (time.perf_counter() - start_time) * 1000
    
    print(f"⚡ Execution time: {execution_time:.2f}ms")
    print(f"🔥 Rules fired: {len(result1.fired_rules)}")
    print()
    
    print("📊 Intermediate Facts (State Flow):")
    for key, value in result1.intermediate_facts.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    print()
    
    print("✅ Final Decision:")
    for key, value in result1.verdict.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    print()
    print()
    
    # Test Case 2: High Risk Customer
    print("Test Case 2: High Risk Customer Profile")
    print("-" * 40)
    
    risky_customer = facts(
        monthly_debt=3500,
        monthly_income=4000,
        current_debt=18000,
        credit_limit=20000,
        employment_years=1,
        annual_income=48000,
        credit_score=580
    )
    
    start_time = time.perf_counter()
    result2 = engine.reason(risky_customer)
    execution_time = (time.perf_counter() - start_time) * 1000
    
    print(f"⚡ Execution time: {execution_time:.2f}ms")
    print(f"🔥 Rules fired: {len(result2.fired_rules)}")
    print()
    
    print("📊 Intermediate Facts (State Flow):")
    for key, value in result2.intermediate_facts.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    print()
    
    print("❌ Final Decision:")
    for key, value in result2.verdict.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    print()
    print()
    
    # Test Case 3: Standard Customer
    print("Test Case 3: Standard Customer Profile")
    print("-" * 40)
    
    standard_customer = facts(
        monthly_debt=1800,
        monthly_income=5500,
        current_debt=8000,
        credit_limit=15000,
        employment_years=5,
        annual_income=66000,
        credit_score=720
    )
    
    start_time = time.perf_counter()
    result3 = engine.reason(standard_customer)
    execution_time = (time.perf_counter() - start_time) * 1000
    
    print(f"⚡ Execution time: {execution_time:.2f}ms")
    print(f"🔥 Rules fired: {len(result3.fired_rules)}")
    print()
    
    print("📊 Intermediate Facts (State Flow):")
    for key, value in result3.intermediate_facts.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    print()
    
    print("✅ Final Decision:")
    for key, value in result3.verdict.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    print()
    print()
    
    # Demonstrate React-style state flow analysis
    print("🧬 React-Style State Flow Analysis")
    print("=" * 50)
    print()
    
    print("Stage 1 (Risk Assessment) creates facts:")
    print("  debt_ratio, credit_utilization, financial_risk, is_low_risk, etc.")
    print()
    
    print("Stage 2 (Customer Segmentation) uses Stage 1 facts:")
    print("  'is_low_risk and annual_income > 80000' → creates customer_tier, base_rate")
    print()
    
    print("Stage 3 (Pricing) uses Stage 1 + Stage 2 facts:")
    print("  'customer_tier is not None and base_rate is not None' → creates final_rate")
    print()
    
    print("Stage 4 (Audit) uses all previous facts:")
    print("  Creates comprehensive decision summary")
    print()
    
    print("🚀 Key Benefits:")
    print("  ✓ Multi-stage computation pipeline")
    print("  ✓ Clean separation of concerns")
    print("  ✓ Reactive state updates")
    print("  ✓ Sub-millisecond performance")
    print("  ✓ Full explainability chain")
    print()
    
    print("💡 This is like React's useState + useEffect, but for business logic!")


if __name__ == "__main__":
    main() 