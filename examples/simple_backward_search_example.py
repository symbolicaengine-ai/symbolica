#!/usr/bin/env python3
"""
Simple Backward Search Example
==============================

Demonstrates simple reverse DAG search to find rules that can achieve goals.
"""

from symbolica import Engine, facts, goal

# Customer approval rules
customer_rules = """
rules:
  - id: "vip_approval"
    priority: 100
    condition: "customer_tier == 'vip' and credit_score > 750"
    actions:
      approved: true
      credit_limit: 50000
    tags: ["vip", "approval"]
  
  - id: "regular_approval"
    priority: 50
    condition: "credit_score > 650 and annual_income > 50000"
    actions:
      approved: true
      credit_limit: 25000
    tags: ["regular", "approval"]
  
  - id: "high_risk_rejection"
    priority: 75
    condition: "previous_defaults > 0 or credit_score < 600"
    actions:
      approved: false
    tags: ["risk", "rejection"]
"""

def demo_reverse_dag_search():
    """Demonstrate reverse DAG search - find rules that can produce a goal."""
    print("=== Reverse DAG Search Demo ===")
    
    engine = Engine.from_yaml(customer_rules)
    
    # Goal: We want approval
    approval_goal = goal(approved=True)
    
    # Find which rules can produce this goal
    supporting_rules = engine.find_rules_for_goal(approval_goal)
    
    print(f"Goal: {approval_goal.target}")
    print(f"Rules that can achieve this goal:")
    for rule in supporting_rules:
        print(f"  • {rule.id}: {rule.condition}")
    print()

def demo_goal_testing():
    """Test if goals can be achieved with specific facts."""
    print("=== Goal Testing Demo ===")
    
    engine = Engine.from_yaml(customer_rules)
    
    # Test cases
    test_cases = [
        {
            "name": "VIP Customer",
            "facts": facts(customer_tier="vip", credit_score=800, annual_income=120000)
        },
        {
            "name": "Regular Customer",  
            "facts": facts(credit_score=700, annual_income=60000)
        },
        {
            "name": "High Risk Customer",
            "facts": facts(credit_score=550, previous_defaults=1)
        }
    ]
    
    approval_goal = goal(approved=True)
    
    for test_case in test_cases:
        achievable = engine.can_achieve_goal(approval_goal, test_case["facts"])
        status = "✅ YES" if achievable else "❌ NO"
        print(f"{test_case['name']}: {status}")
    print()

def demo_multiple_goals():
    """Test multiple different goals."""
    print("=== Multiple Goals Demo ===")
    
    engine = Engine.from_yaml(customer_rules)
    
    # Customer facts
    customer = facts(customer_tier="vip", credit_score=800, annual_income=120000)
    
    # Different goals to test
    goals_to_test = [
        goal(approved=True),
        goal(credit_limit=50000),
        goal(approved=False)
    ]
    
    print(f"Customer: {customer.data}")
    print()
    
    for test_goal in goals_to_test:
        # Find supporting rules
        rules = engine.find_rules_for_goal(test_goal)
        rule_names = [r.id for r in rules]
        
        # Test if achievable
        achievable = engine.can_achieve_goal(test_goal, customer)
        status = "✅" if achievable else "❌"
        
        print(f"{status} {test_goal.target}")
        print(f"   Supporting rules: {rule_names}")
        print()

if __name__ == "__main__":
    print("Simple Backward Search Demo")
    print("=" * 40)
    print()
    
    demo_reverse_dag_search()
    print("-" * 30)
    demo_goal_testing()
    print("-" * 30)
    demo_multiple_goals()
    
    print("=== Demo Complete ===")
    print("Simple backward search provides:")
    print("✅ Reverse DAG search to find supporting rules")
    print("✅ Boolean test if goal is achievable")
    print("✅ Clean, minimal API") 