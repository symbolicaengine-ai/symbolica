"""
Complex Logical Conditions Example

This example demonstrates Symbolica's powerful structured condition syntax
using ANY, ALL, and NOT operators to build sophisticated business logic.

Key concepts:
- Nested logical structures with ANY/ALL/NOT
- Complex eligibility and approval workflows
- Real-world insurance underwriting scenarios
- Combining simple conditions into complex rules

Run: python example.py
"""

from symbolica import Engine, facts
from symbolica.core.models import Rule
from symbolica.core.services.loader import ConditionParser
import json

def main():
    """Demonstrate complex logical conditions in Symbolica"""
    
    print("Symbolica Complex Conditions Example")
    print("=" * 45)
    
    # Create engine with inline complex condition rules
    engine = create_engine_with_complex_rules()
    
    print(f"Loaded {len(engine._rules)} underwriting rules")
    print("\nDemonstrating complex logical conditions...")
    
    # Test Case 1: Young driver with excellent record
    print("\n" + "="*50)
    print("Test Case 1: Young driver with excellent record")
    print("="*50)
    
    young_excellent_driver = facts(
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
    
    result = engine.reason(young_excellent_driver)
    print_result("Young Excellent Driver", result)
    
    # Test Case 2: Middle-aged driver with mixed record
    print("\n" + "="*50)
    print("Test Case 2: Middle-aged driver with mixed record")
    print("="*50)
    
    mixed_record_driver = facts(
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
    
    result = engine.reason(mixed_record_driver)
    print_result("Mixed Record Driver", result)
    
    # Test Case 3: High-risk young driver
    print("\n" + "="*50)
    print("Test Case 3: High-risk young driver")
    print("="*50)
    
    high_risk_driver = facts(
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
    
    result = engine.reason(high_risk_driver)
    print_result("High-Risk Driver", result)
    
    # Test Case 4: Senior driver with clean record
    print("\n" + "="*50)
    print("Test Case 4: Senior driver with clean record")
    print("="*50)
    
    senior_driver = facts(
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
    
    result = engine.reason(senior_driver)
    print_result("Senior Driver", result)
    
    # Test Case 5: Commercial vehicle operator
    print("\n" + "="*50)
    print("Test Case 5: Commercial vehicle operator")
    print("="*50)
    
    commercial_driver = facts(
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
    
    result = engine.reason(commercial_driver)
    print_result("Commercial Driver", result)
    
    # Demonstrate condition analysis
    print("\n" + "="*60)
    print("Complex Condition Structure Analysis")
    print("="*60)
    
    analyze_complex_conditions()

def create_engine_with_complex_rules():
    """Create Symbolica engine with inline complex condition rules"""
    
    engine = Engine()
    
    # Define complex condition rules inline
    complex_rules = [
        # Premium Customer Qualification (Complex ALL with nested ANY)
        Rule(
            id="premium_customer_qualification",
            priority=100,
            condition=ConditionParser.convert_condition({
                "all": [
                    "age >= 25",
                    "driving_experience_years >= 5",
                    {
                        "any": [
                            "credit_score >= 700",
                            {
                                "all": [
                                    "credit_score >= 650",
                                    "previous_insurance == True",
                                    "coverage_lapse_months <= 6"
                                ]
                            }
                        ]
                    },
                    {
                        "not": {
                            "any": [
                                "accidents_last_3_years >= 2",
                                "tickets_last_3_years >= 3"
                            ]
                        }
                    }
                ]
            }),
            actions={
                "status": "approved",
                "premium_tier": "premium",
                "risk_level": "low",
                "base_premium": 1200,
                "discount_rate": 0.15,
                "discounts": ["good_driver", "premium_customer"],
                "surcharge_rate": 0.0,
                "credit_score_factor": 1.0
            },
            tags=["premium", "low_risk"]
        ),
        
        # Standard Customer with Good Record
        Rule(
            id="standard_good_driver",
            priority=90,
            condition=ConditionParser.convert_condition({
                "all": [
                    "age >= 21",
                    "driving_experience_years >= 3",
                    "accidents_last_3_years <= 1",
                    "tickets_last_3_years <= 2",
                    {
                        "any": [
                            "credit_score >= 650",
                            {
                                "all": [
                                    "previous_insurance == True",
                                    "coverage_lapse_months <= 12"
                                ]
                            }
                        ]
                    },
                    {
                        "not": {
                            "all": [
                                "age < 25",
                                "vehicle_type == 'sports_car'",
                                "annual_mileage > 15000"
                            ]
                        }
                    }
                ]
            }),
            actions={
                "status": "approved",
                "premium_tier": "standard",
                "risk_level": "medium",
                "base_premium": 1800,
                "discount_rate": 0.10,
                "discounts": ["good_driver"],
                "surcharge_rate": 0.0,
                "credit_score_factor": 1.0
            },
            tags=["standard", "medium_risk"]
        ),
        
        # Young Driver Special Consideration (Complex nested conditions)
        Rule(
            id="young_driver_special",
            priority=85,
            condition=ConditionParser.convert_condition({
                "all": [
                    "age < 25",
                    "driving_experience_years >= 2",
                    {
                        "any": [
                            {
                                "all": [
                                    "accidents_last_3_years == 0",
                                    "tickets_last_3_years == 0",
                                    {
                                        "any": [
                                            "education == 'college_graduate'",
                                            "occupation == 'engineer'",
                                            "occupation == 'teacher'"
                                        ]
                                    }
                                ]
                            },
                            {
                                "all": [
                                    "accidents_last_3_years <= 1",
                                    "tickets_last_3_years <= 1",
                                    "credit_score >= 720",
                                    "previous_insurance == True"
                                ]
                            }
                        ]
                    },
                    {
                        "not": {
                            "any": [
                                "vehicle_type == 'sports_car'",
                                "vehicle_type == 'motorcycle'",
                                "annual_mileage > 20000"
                            ]
                        }
                    }
                ]
            }),
            actions={
                "status": "approved",
                "premium_tier": "young_driver",
                "risk_level": "medium_high",
                "base_premium": 2400,
                "discount_rate": 0.05,
                "discounts": ["good_student", "young_professional"],
                "special_conditions": ["defensive_driving_course_recommended"],
                "surcharge_rate": 0.0,
                "credit_score_factor": 1.0
            },
            tags=["young_driver", "special_consideration"]
        ),
        
        # High-Risk Denial Conditions (Complex exclusions)
        Rule(
            id="high_risk_denial",
            priority=110,
            condition=ConditionParser.convert_condition({
                "any": [
                    {
                        "all": [
                            "age < 21",
                            {
                                "any": [
                                    "accidents_last_3_years >= 2",
                                    "tickets_last_3_years >= 4",
                                    "vehicle_type == 'sports_car'"
                                ]
                            }
                        ]
                    },
                    {
                        "all": [
                            "accidents_last_3_years >= 3",
                            {
                                "any": [
                                    "tickets_last_3_years >= 3",
                                    "credit_score < 500"
                                ]
                            }
                        ]
                    },
                    {
                        "all": [
                            "previous_insurance == False",
                            "coverage_lapse_months > 24",
                            {
                                "any": [
                                    "accidents_last_3_years >= 2",
                                    "age < 25"
                                ]
                            }
                        ]
                    }
                ]
            }),
            actions={
                "status": "denied",
                "denial_reasons": ["high_risk_profile", "unacceptable_driving_record"]
            },
            tags=["denial", "high_risk"]
        ),
        
        # Multi-Factor Discount Qualification
        Rule(
            id="multi_factor_discount",
            priority=60,
            condition=ConditionParser.convert_condition({
                "all": [
                    "accidents_last_3_years == 0",
                    "tickets_last_3_years == 0",
                    {
                        "any": [
                            {
                                "all": [
                                    "marital_status == 'married'",
                                    "age >= 30",
                                    "credit_score >= 700"
                                ]
                            },
                            {
                                "all": [
                                    "education == 'college_graduate'",
                                    "occupation == 'engineer'",
                                    "previous_insurance == True"
                                ]
                            },
                            {
                                "all": [
                                    "location == 'suburban'",
                                    "annual_mileage <= 10000",
                                    "vehicle_age >= 3"
                                ]
                            }
                        ]
                    },
                    {
                        "not": {
                            "any": [
                                "coverage_lapse_months > 0",
                                "vehicle_type == 'sports_car'"
                            ]
                        }
                    }
                ]
            }),
            actions={
                "additional_discount_rate": 0.05,
                "discounts": ["multi_factor_bonus"]
            },
            tags=["discount", "low_risk"]
        ),
        
        # Comprehensive Risk Assessment (All factors combined)
        Rule(
            id="comprehensive_risk_assessment",
            priority=40,
            condition=ConditionParser.convert_condition({
                "all": [
                    {
                        "not": {
                            "any": [
                                "status == 'denied'",
                                "status == 'approved'"
                            ]
                        }
                    },
                    {
                        "any": [
                            {
                                "all": [
                                    "age >= 25",
                                    "age <= 65",
                                    "driving_experience_years >= 5",
                                    "accidents_last_3_years <= 1",
                                    "tickets_last_3_years <= 2"
                                ]
                            },
                            {
                                "all": [
                                    "previous_insurance == True",
                                    "coverage_lapse_months <= 12",
                                    "credit_score >= 600",
                                    {
                                        "not": {
                                            "all": [
                                                "accidents_last_3_years >= 2",
                                                "tickets_last_3_years >= 2"
                                            ]
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }),
            actions={
                "status": "approved",
                "premium_tier": "standard_risk",
                "risk_level": "medium",
                "base_premium": 2000,
                "discount_rate": 0.0,
                "surcharge_rate": 0.0,
                "credit_score_factor": 1.0
            },
            tags=["standard", "fallback"]
        ),
        
        # Final Premium Calculation (Applies to all approved cases)
        Rule(
            id="final_premium_calculation",
            priority=10,
            condition="status == 'approved'",
            actions={
                "total_premium": "{{ (base_premium * (1 - discount_rate + surcharge_rate + additional_discount_rate) * credit_score_factor)|round|int }}"
            },
            tags=["calculation", "final"]
        )
    ]
    
    # Add rules to engine
    for rule in complex_rules:
        engine.add_rule(rule)
        
    return engine

def print_result(test_name, result):
    """Print formatted test results"""
    print(f"\n{test_name} Results:")
    print(f"  Status: {result.verdict.get('status', 'Unknown')}")
    print(f"  Premium Tier: {result.verdict.get('premium_tier', 'N/A')}")
    print(f"  Risk Level: {result.verdict.get('risk_level', 'N/A')}")
    
    if result.verdict.get('approved', False) or result.verdict.get('status') == 'approved':
        base_premium = result.verdict.get('base_premium', 0)
        total_premium = result.verdict.get('total_premium', 0)
        
        # Handle case where total_premium might be None or string
        if isinstance(total_premium, (int, float)) and total_premium > 0:
            print(f"  Base Premium: ${base_premium:,}")
            print(f"  Total Premium: ${int(total_premium):,}")
        else:
            print(f"  Base Premium: ${base_premium:,}")
            print(f"  Total Premium: Calculation pending")
        
        discounts = result.verdict.get('discounts', [])
        if discounts:
            print(f"  Discounts Applied: {', '.join(discounts)}")
            
        surcharges = result.verdict.get('surcharges', [])
        if surcharges:
            print(f"  Surcharges Applied: {', '.join(surcharges)}")
    else:
        denial_reasons = result.verdict.get('denial_reasons', [])
        if denial_reasons:
            print(f"  Denial Reasons: {', '.join(denial_reasons)}")
    
    special_conditions = result.verdict.get('special_conditions', [])
    if special_conditions:
        print(f"  Special Conditions: {', '.join(special_conditions)}")
    
    print(f"  Execution Time: {result.execution_time_ms:.2f}ms")
    print(f"  Rules Fired: {len(result.fired_rules)}")
    
    # Show reasoning for complex conditions
    print(f"\n  Reasoning:")
    for line in result.reasoning.split('\n'):
        if line.strip():
            print(f"    {line}")

def analyze_complex_conditions():
    """Analyze and explain the complex condition structures"""
    
    print("\nComplex Condition Patterns Used:")
    print("\n1. ALL with nested ANY conditions:")
    print("   - Must satisfy ALL top-level requirements")
    print("   - Can satisfy ANY of the nested alternatives")
    print("   - Example: Low risk = good record AND (experienced OR mature)")
    
    print("\n2. NOT conditions for exclusions:")
    print("   - Explicitly exclude certain scenarios")
    print("   - Example: NOT (high-risk vehicle AND inexperienced)")
    
    print("\n3. Mixed logical operators:")
    print("   - Combine AND, OR, NOT in sophisticated ways")
    print("   - Model real-world business logic accurately")
    
    print("\n4. Nested condition benefits:")
    print("   - More readable than complex boolean expressions")
    print("   - Easier to maintain and modify")
    print("   - Better error messages and debugging")
    print("   - Matches how business analysts think")
    
    print("\nCondition Complexity Examples:")
    
    # Show some example condition structures
    examples = [
        {
            "name": "Premium Customer Eligibility",
            "structure": {
                "all": [
                    "age >= 25",
                    "driving_experience_years >= 5",
                    {"any": [
                        "credit_score >= 700",
                        {"all": [
                            "credit_score >= 650",
                            "previous_insurance == True",
                            "coverage_lapse_months <= 6"
                        ]}
                    ]},
                    {"not": {
                        "any": [
                            "accidents_last_3_years >= 2",
                            "tickets_last_3_years >= 3"
                        ]
                    }}
                ]
            }
        },
        {
            "name": "High-Risk Vehicle Surcharge",
            "structure": {
                "any": [
                    {"all": [
                        "vehicle_type == 'sports_car'",
                        "vehicle_value > 40000"
                    ]},
                    {"all": [
                        "vehicle_type == 'motorcycle'",
                        "age < 30"
                    ]},
                    {"all": [
                        "vehicle_type == 'commercial_truck'",
                        {"not": "commercial_license == True"}
                    ]}
                ]
            }
        }
    ]
    
    for example in examples:
        print(f"\n  {example['name']}:")
        print(f"    {json.dumps(example['structure'], indent=6)}")

if __name__ == "__main__":
    main() 