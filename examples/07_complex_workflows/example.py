#!/usr/bin/env python3
"""
Complex Workflows Example
=========================

This example demonstrates a sophisticated workflow combining all Symbolica features:
- LLM integration for intelligent decision making
- Custom functions for business logic
- Rule chaining for workflow automation
- Temporal functions for monitoring
- Multiple rule files for organization
- Backward chaining for goal analysis

Setup:
pip install openai
export OPENAI_API_KEY="your-api-key-here"
"""

import sys
import os
import time
import random
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from symbolica import Engine, facts, goal

def main():
    print("Complex Workflows Example")
    print("=" * 50)
    
    # Check for OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: Please set your OPENAI_API_KEY environment variable")
        print("Example: export OPENAI_API_KEY='your-api-key-here'")
        return
    
    # Import and create OpenAI client
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        print("OpenAI client initialized successfully")
    except ImportError:
        print("Error: Please install the OpenAI library: pip install openai")
        return
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        return
    
    # Load multiple rule files
    engine = Engine.from_directory("rules/", llm_client=client)
    
    # Register custom business functions
    register_custom_functions(engine)
    
    print(f"Loaded {len(engine.rules)} rules from multiple files")
    print("Features combined: LLM + Custom Functions + Chaining + Temporal + Monitoring")
    
    # Initialize monitoring data
    initialize_monitoring_data(engine)
    
    # Test scenarios
    scenarios = [
        {
            "name": "VIP Customer - Perfect Profile",
            "data": facts(
                application_data="VIP customer with excellent credit history, stable high income, long employment",
                credit_score=820,
                income=150000,
                debt_ratio=0.15,
                loan_amount=50000,
                avg_transaction=45000,
                customer_tier="vip"
            )
        },
        {
            "name": "Standard Customer - Good Profile", 
            "data": facts(
                application_data="Standard customer with good credit score, stable middle income, regular employment",
                credit_score=720,
                income=75000,
                debt_ratio=0.35,
                loan_amount=30000,
                avg_transaction=25000,
                customer_tier="standard"
            )
        },
        {
            "name": "High Risk - Poor Credit",
            "data": facts(
                application_data="Customer with poor credit history, multiple previous defaults, lower income",
                credit_score=580,
                income=40000,
                debt_ratio=0.65,
                loan_amount=25000,
                avg_transaction=15000,
                customer_tier="standard"
            )
        },
        {
            "name": "Fraud Alert - Suspicious Pattern",
            "data": facts(
                application_data="Customer with good credit but requesting unusually large loan amount compared to transaction history",
                credit_score=750,
                income=80000,
                debt_ratio=0.25,
                loan_amount=200000,  # Much larger than usual
                avg_transaction=20000,
                customer_tier="standard"
            )
        }
    ]
    
    for i, scenario in enumerate(scenarios):
        print(f"\nScenario {i+1}: {scenario['name']}")
        print("-" * 60)
        
        # Record metrics for monitoring
        record_scenario_metrics(engine, scenario['name'])
        
        # Process application
        start_time = time.perf_counter()
        
        print(f"Input: {scenario['data']['application_data']}")
        print("Processing with AI analysis...")
        
        result = engine.reason(scenario['data'])
        processing_time = (time.perf_counter() - start_time) * 1000
        
        print(f"Processing time: {processing_time:.2f}ms")
        print(f"Rules fired: {result.fired_rules}")
        print(f"Final result: {result.verdict}")
        
        # Show workflow progression
        if result.fired_rules:
            analyze_workflow_progression(result.reasoning)
        
        # Update monitoring metrics
        update_monitoring_metrics(engine, result.verdict, processing_time)
    
    # Check monitoring alerts
    print(f"\nMonitoring & Alerting:")
    print("-" * 30)
    monitoring_result = engine.reason(facts())
    if monitoring_result.fired_rules:
        print(f"Monitoring alerts: {monitoring_result.fired_rules}")
        print(f"Alert details: {monitoring_result.verdict}")
    else:
        print("No monitoring alerts triggered")
    
    # Demonstrate goal analysis
    print(f"\nGoal Analysis:")
    print("-" * 20)
    demonstrate_goal_analysis(engine)
    
    # Show comprehensive statistics
    print(f"\nComprehensive Statistics:")
    print("-" * 30)
    show_system_statistics(engine)

def register_custom_functions(engine):
    """Register all custom business functions."""
    engine.register_function("risk_score", calculate_risk_score, allow_unsafe=True)
    engine.register_function("fraud_check", detect_fraud, allow_unsafe=True)
    engine.register_function("current_timestamp", lambda: datetime.now().isoformat())
    engine.register_function("generate_account_number", lambda: f"ACC{random.randint(1000000, 9999999)}")
    engine.register_function("calculate_delivery_date", lambda: (datetime.now() + timedelta(days=random.randint(3, 7))).strftime("%Y-%m-%d"))

def calculate_risk_score(credit_score, income, debt_ratio):
    """Enhanced risk calculation."""
    credit_factor = (credit_score - 300) / 550
    income_factor = min(income / 100000, 1.0)
    debt_factor = max(0, 1.0 - debt_ratio)
    
    composite = (credit_factor * 0.5) + (income_factor * 0.3) + (debt_factor * 0.2)
    
    if composite >= 0.7:
        return "low"
    elif composite >= 0.4:
        return "medium"
    else:
        return "high"

def detect_fraud(loan_amount, avg_transaction):
    """Enhanced fraud detection."""
    return loan_amount > avg_transaction * 5 or loan_amount > 150000

def initialize_monitoring_data(engine):
    """Initialize baseline monitoring data."""
    # Simulate historical data
    for _ in range(50):
        engine.store_datapoint("approvals", 1)
        engine.store_datapoint("ai_response_time", random.uniform(800, 1200))
    
    for _ in range(5):
        engine.store_datapoint("fraud_detected", 1)

def record_scenario_metrics(engine, scenario_name):
    """Record metrics for each scenario."""
    # Simulate AI response time variation
    response_time = random.uniform(600, 2500)
    engine.store_datapoint("ai_response_time", response_time)

def update_monitoring_metrics(engine, verdict, processing_time):
    """Update monitoring metrics based on results."""
    if verdict.get('approved'):
        engine.store_datapoint("approvals", 1)
    
    if verdict.get('fraud_detected') or verdict.get('flagged_for_review'):
        engine.store_datapoint("fraud_detected", 1)

def analyze_workflow_progression(reasoning):
    """Analyze and display workflow progression."""
    print("Workflow progression:")
    steps = reasoning.split('\n')
    step_num = 1
    
    for step in steps:
        if step.strip().startswith('✓'):
            step_clean = step.strip()[2:].split(':')[0]
            if 'triggered by' in step:
                trigger_info = step.split('(triggered by')[1].strip(')')
                print(f"  Step {step_num}: {step_clean} (triggered by {trigger_info})")
            else:
                print(f"  Step {step_num}: {step_clean}")
            step_num += 1

def demonstrate_goal_analysis(engine):
    """Demonstrate backward chaining goal analysis."""
    # Define goal: successful customer onboarding
    onboarding_goal = goal(initial_setup_complete=True)
    
    print(f"Goal: Complete customer onboarding")
    
    # Find supporting rules
    supporting_rules = engine.find_rules_for_goal(onboarding_goal)
    print(f"Rules that can achieve this goal: {len(supporting_rules)}")
    
    for rule in supporting_rules[:3]:  # Show first 3
        print(f"  - {rule.id}: {rule.condition}")
    
    # Test achievability
    test_facts = facts(approved=True, customer_tier="vip")
    can_achieve = engine.can_achieve_goal(onboarding_goal, test_facts)
    print(f"Can achieve with approved VIP customer: {can_achieve}")

def show_system_statistics(engine):
    """Show comprehensive system statistics."""
    print(f"Total rules in system: {len(engine.rules)}")
    
    # Count rules by feature type
    rule_counts = {
        'AI-powered': len([r for r in engine.rules if 'PROMPT(' in r.condition]),
        'Custom functions': len([r for r in engine.rules if any(func in r.condition for func in ['risk_score', 'fraud_check'])]),
        'Temporal': len([r for r in engine.rules if any(temp in r.condition for temp in ['recent_', 'sustained_'])]),
        'Chaining': len([r for r in engine.rules if r.triggers])
    }
    
    print("Rule distribution by feature:")
    for feature, count in rule_counts.items():
        print(f"  - {feature}: {count} rules")
    
    print(f"Features demonstrated:")
    print(f"  - Hybrid AI-Rule decision making with real OpenAI API")
    print(f"  - Multi-file rule organization") 
    print(f"  - Real-time monitoring and alerting")
    print(f"  - Complex workflow automation")
    print(f"  - Goal-directed planning")

if __name__ == "__main__":
    main() 