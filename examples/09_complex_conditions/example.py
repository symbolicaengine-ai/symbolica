#!/usr/bin/env python3
"""
Complex Logical Conditions Example
==================================

This example demonstrates Symbolica's powerful structured condition syntax
using ANY, ALL, and NOT operators to build sophisticated business logic.

Key concepts:
- Nested logical structures with ANY/ALL/NOT
- Complex eligibility and approval workflows  
- Real-world insurance underwriting scenarios
- Combining simple conditions into complex rules

Run: python example.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from symbolica import Engine, facts

def main():
    print("Complex Logical Conditions Demo")
    print("=" * 40)
    
    # Load complex condition rules from YAML
    engine = Engine.from_file("insurance_underwriting_rules.yaml")
    
    print(f"Loaded {len(engine.rules)} insurance underwriting rules")
    print("Demonstrating complex logical conditions...")
    
    # Test scenarios
    scenarios = [
        ("Young Excellent Driver", create_young_excellent_driver(), "Should approve with special consideration"),
        ("Mixed Record Driver", create_mixed_record_driver(), "Should approve as premium customer"),
        ("High-Risk Driver", create_high_risk_driver(), "Should deny due to risk factors"),
        ("Senior Driver", create_senior_driver(), "Should approve with discounts"),
        ("Commercial Driver", create_commercial_driver(), "Should approve as professional"),
    ]
    
    print(f"\nTesting {len(scenarios)} underwriting scenarios...")
    
    for name, data, expected in scenarios:
        print(f"\n{name}: {expected}")
        
        result = engine.reason(data)
        
        # Analyze results
        status = result.verdict.get('status', 'pending')
        premium_tier = result.verdict.get('premium_tier', 'N/A')
        risk_level = result.verdict.get('risk_level', 'N/A')
        
        status_display = []
        if status == 'approved':
            status_display.append("APPROVED")
        elif status == 'denied':
            status_display.append("DENIED")
        else:
            status_display.append("PENDING")
            
        if premium_tier != 'N/A':
            status_display.append(f"{premium_tier.upper()}")
            
        if risk_level != 'N/A':
            status_display.append(f"{risk_level.upper()}")
        
        print(f"  Result: {' | '.join(status_display)}")
        
        # Show premium details for approved cases
        if status == 'approved':
            base_premium = result.verdict.get('base_premium', 0)
            total_premium = result.verdict.get('total_premium', 0)
            discounts = result.verdict.get('discounts', [])
            
            print(f"  Base Premium: ${base_premium:,}")
            if isinstance(total_premium, (int, float)) and total_premium > 0:
                print(f"  Total Premium: ${int(total_premium):,}")
            
            if discounts:
                print(f"  Discounts: {', '.join(discounts)}")
                
        elif status == 'denied':
            denial_reasons = result.verdict.get('denial_reasons', [])
            if denial_reasons:
                print(f"  Denial Reasons: {', '.join(denial_reasons)}")
        
        special_conditions = result.verdict.get('special_conditions', [])
        if special_conditions:
            print(f"  Special Conditions: {', '.join(special_conditions)}")
        
        print(f"  Rules Fired: {len(result.fired_rules)}")

def create_young_excellent_driver():
    return facts(
        age=22,
        driving_experience_years=4,
        accidents_last_3_years=0,
        tickets_last_3_years=0,
        credit_score=780,
        vehicle_type="sedan",
        vehicle_age=2,
        vehicle_value=25000,
        annual_mileage=8000,
        location="suburban",
        marital_status="single",
        education="college_graduate",
        occupation="engineer",
        previous_insurance=True,
        coverage_lapse_months=0
    )

def create_mixed_record_driver():
    return facts(
        age=35,
        driving_experience_years=17,
        accidents_last_3_years=1,
        tickets_last_3_years=2,
        credit_score=650,
        vehicle_type="suv",
        vehicle_age=5,
        vehicle_value=35000,
        annual_mileage=15000,
        location="urban",
        marital_status="married",
        education="high_school",
        occupation="sales",
        previous_insurance=True,
        coverage_lapse_months=3
    )

def create_high_risk_driver():
    return facts(
        age=19,
        driving_experience_years=1,
        accidents_last_3_years=2,
        tickets_last_3_years=3,
        credit_score=580,
        vehicle_type="sports_car",
        vehicle_age=1,
        vehicle_value=50000,
        annual_mileage=20000,
        location="urban",
        marital_status="single",
        education="high_school",
        occupation="student",
        previous_insurance=False,
        coverage_lapse_months=0
    )

def create_senior_driver():
    return facts(
        age=68,
        driving_experience_years=50,
        accidents_last_3_years=0,
        tickets_last_3_years=0,
        credit_score=750,
        vehicle_type="sedan",
        vehicle_age=3,
        vehicle_value=30000,
        annual_mileage=6000,
        location="suburban",
        marital_status="married",
        education="college_graduate",
        occupation="retired",
        previous_insurance=True,
        coverage_lapse_months=0
    )

def create_commercial_driver():
    return facts(
        age=40,
        driving_experience_years=22,
        accidents_last_3_years=0,
        tickets_last_3_years=1,
        credit_score=700,
        vehicle_type="commercial_truck",
        vehicle_age=4,
        vehicle_value=80000,
        annual_mileage=50000,
        location="rural",
        marital_status="married",
        education="high_school",
        occupation="truck_driver",
        previous_insurance=True,
        coverage_lapse_months=0,
        commercial_license=True,
        years_commercial_driving=15
    )
if __name__ == "__main__":
    main() 