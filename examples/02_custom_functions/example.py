#!/usr/bin/env python3
"""
Custom Functions Example
========================

This example demonstrates how to extend Symbolica with custom business logic:
- Registering safe lambda functions (recommended)
- Using custom functions in rule conditions
- Complex business logic encapsulation
- Safe function execution
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from symbolica import Engine, facts

def main():
    print("Custom Functions Example")
    print("=" * 50)
    
    engine = Engine.from_file("loan_analysis.yaml")
    
    # Register custom business logic functions using LAMBDA FUNCTIONS (recommended)
    # print("Registering lambda functions (safe by default):")
    
    # Risk scoring as a lambda function
    engine.register_function("risk_score", 
        lambda credit, income, debt: (
            "low" if credit >= 700 and income >= 60000 and debt <= 0.3 else
            "medium" if credit >= 600 and income >= 40000 and debt <= 0.5 else
            "high"
        )
    )
    # print("risk_score: lambda function for credit risk assessment")
    
    # Fraud detection as a lambda function
    engine.register_function("fraud_check",
        lambda amount, avg_tx: amount > avg_tx * 4 or amount > 200000
    )
    print("fraud_check: lambda function for fraud detection")
    
    # Test case 1: Low risk customer
    print("\nTest 1: Low Risk Customer")
    low_risk = facts(
        credit_score=780,
        income=80000,
        debt_ratio=0.2,
        loan_amount=25000,
        avg_transaction=20000
    )
    
    result = engine.reason(low_risk)
    print(f"Input: {low_risk.data}")
    print(f"Result: {result.verdict}")
    print(f"Fired rules: {result.fired_rules}")
    print(f"Execution time: {result.execution_time_ms:.2f}ms")
    print(f"Reasoning: {result.reasoning}")
    
    # Test case 2: Medium risk customer
    print("\nTest 2: Medium Risk Customer")
    medium_risk = facts(
        credit_score=650,
        income=50000,
        debt_ratio=0.45,
        loan_amount=30000,
        avg_transaction=25000
    )
    
    result = engine.reason(medium_risk)
    print(f"Input: Credit {medium_risk['credit_score']}, Income ${medium_risk['income']:,}, Debt ratio {medium_risk['debt_ratio']}")
    print(f"Result: {result.verdict}")
    print(f"Reasoning: {result.reasoning}")
    
    # Test case 3: High risk customer
    print("\nTest 3: High Risk Customer")
    high_risk = facts(
        credit_score=550,
        income=30000,
        debt_ratio=0.8,
        loan_amount=40000,
        avg_transaction=10000
    )
    
    result = engine.reason(high_risk)
    print(f"Input: Credit {high_risk['credit_score']}, Income ${high_risk['income']:,}, Debt ratio {high_risk['debt_ratio']}")
    print(f"Result: {result.verdict}")
    print(f"Reasoning: {result.reasoning}")
    
    # Test case 4: Fraud detection
    print("\nTest 4: Potential Fraud")
    fraud_case = facts(
        credit_score=720,
        income=70000,
        debt_ratio=0.3,
        loan_amount=100000,  # Much larger than usual
        avg_transaction=15000
    )
    
    result = engine.reason(fraud_case)
    print(f"Input: Credit {fraud_case['credit_score']}, Loan ${fraud_case['loan_amount']:,}, Avg transaction ${fraud_case['avg_transaction']:,}")
    print(f"Result: {result.verdict}")
    print(f"Reasoning: {result.reasoning}")
    
    # Show function results directly
    print("\nDirect Function Testing:")
    test_cases = [
        (780, 80000, 0.2),
        (650, 50000, 0.45),
        (550, 30000, 0.8)
    ]
    
    # Test the lambda function logic
    for credit, income, debt in test_cases:
        risk = "low" if credit >= 700 and income >= 60000 and debt <= 0.3 else \
               "medium" if credit >= 600 and income >= 40000 and debt <= 0.5 else "high"
        print(f"  Credit {credit}, Income ${income:,}, Debt {debt:.1f} -> Risk: {risk}")

if __name__ == "__main__":
    main() 