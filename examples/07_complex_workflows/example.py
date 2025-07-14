#!/usr/bin/env python3
"""
Simple Complex Workflows Demo
============================

Clean demonstration of complex workflows with:
- AI + traditional risk assessment
- Fraud detection and case management
- Basic monitoring and alerting
- Complete workflow automation
"""

import sys
import os
import time
import random
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from symbolica import Engine, facts

def main():
    print("Complex Workflows Demo")
    print("=" * 40)
    
    # Setup engine
    engine = setup_engine()
    
    # Test scenarios
    scenarios = [
        ("VIP Customer", create_vip_customer(), "Should approve with VIP treatment"),
        ("Good Customer", create_good_customer(), "Should approve normally"),
        ("Borderline", create_borderline_customer(), "Should approve with conditions"),
        ("High Risk", create_high_risk_customer(), "Should reject"),
        ("Fraud Case", create_fraud_case(), "Should detect fraud"),
    ]
    
    print(f"Testing {len(scenarios)} scenarios...")
    
    for name, data, expected in scenarios:
        print(f"\n{name}: {expected}")
        
        start_time = time.perf_counter()
        result = engine.reason(data)
        processing_time = (time.perf_counter() - start_time) * 1000
        
        # Simple analysis
        approved = result.verdict.get('approved', False)
        fraud = result.verdict.get('flagged_for_review', False)
        vip = result.verdict.get('welcome_package_sent', False)
        
        status = []
        if approved:
            status.append("APPROVED")
        else:
            status.append("DENIED")
        if fraud:
            status.append("FRAUD")
        if vip:
            status.append("VIP")
        
        print(f"  Result: {' | '.join(status)}")
        print(f"  Rules: {len(result.fired_rules)}, Time: {processing_time:.0f}ms")
    
    # Test monitoring
    print(f"\nMonitoring Test:")
    test_monitoring(engine)

def setup_engine():
    """Setup engine with simple functions."""
    # Try AI integration
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            engine = Engine.from_directory("rules/", llm_client=client)
            print("AI enabled")
        except:
            engine = Engine.from_directory("rules/")
            print("AI disabled")
    else:
        engine = Engine.from_directory("rules/")
        print("AI disabled")
    
    # Register simple functions
    engine.register_function("risk_score", simple_risk_score, allow_unsafe=True)
    engine.register_function("fraud_check", simple_fraud_check, allow_unsafe=True)
    engine.register_function("current_timestamp", lambda: datetime.now().isoformat())
    engine.register_function("generate_account_number", lambda: f"ACC{random.randint(1000000, 9999999)}")
    engine.register_function("calculate_delivery_date", lambda: "2025-07-20")
    
    return engine

def simple_risk_score(credit_score, income, debt_ratio):
    """Simplified risk scoring."""
    try:
        credit_score = float(credit_score or 300)
        income = float(income or 0)
        debt_ratio = float(debt_ratio or 1.0)
        
        # Simple scoring
        if credit_score >= 750 and income >= 80000 and debt_ratio <= 0.3:
            return "low"
        elif credit_score >= 650 and income >= 50000 and debt_ratio <= 0.5:
            return "medium"
        else:
            return "high"
    except:
        return "high"

def simple_fraud_check(loan_amount, avg_transaction):
    """Simplified fraud detection."""
    try:
        loan_amount = float(loan_amount or 0)
        avg_transaction = float(avg_transaction or 0)
        
        # Clear fraud indicators
        if loan_amount > 200000:  # Large loan
            return True
        if avg_transaction > 0 and loan_amount > avg_transaction * 10:  # 10x mismatch
            return True
        
        return False
    except:
        return True

def create_vip_customer():
    return facts(
        application_data="VIP customer with excellent credit",
        credit_score=820,
        income=200000,
        debt_ratio=0.1,
        loan_amount=50000,
        avg_transaction=80000,
        customer_tier="vip"
    )

def create_good_customer():
    return facts(
        application_data="Good customer with stable income",
        credit_score=720,
        income=75000,
        debt_ratio=0.3,
        loan_amount=30000,
        avg_transaction=30000,
        customer_tier="standard"
    )

def create_borderline_customer():
    return facts(
        application_data="Borderline customer with some risk",
        credit_score=650,
        income=50000,
        debt_ratio=0.5,
        loan_amount=25000,
        avg_transaction=20000,
        customer_tier="standard"
    )

def create_high_risk_customer():
    return facts(
        application_data="High risk customer",
        credit_score=580,
        income=35000,
        debt_ratio=0.7,
        loan_amount=30000,
        avg_transaction=10000,
        customer_tier="standard"
    )

def create_fraud_case():
    return facts(
        application_data="Suspicious large loan request",
        credit_score=750,
        income=80000,
        debt_ratio=0.2,
        loan_amount=500000,  # Very large - should trigger fraud
        avg_transaction=15000,
        customer_tier="standard"
    )

def test_monitoring(engine):
    """Test monitoring system."""
    # Add some monitoring data
    for _ in range(20):
        engine.store_datapoint("approvals", 1)
        engine.store_datapoint("ai_response_time", 1500)
    
    # Add fraud cases
    for _ in range(8):
        engine.store_datapoint("fraud_detected", 1)
    
    # Check monitoring
    result = engine.reason(facts())
    
    monitoring_alerts = [rule for rule in result.fired_rules if 'monitoring' in str(rule) or 'alert' in str(rule)]
    if monitoring_alerts:
        print(f"Alerts: {monitoring_alerts}")
    else:
        print(f"No alerts")

if __name__ == "__main__":
    main() 