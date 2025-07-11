#!/usr/bin/env python3
"""
Backward Chaining Example
=========================

This example demonstrates backward chaining and goal-directed reasoning:
- Finding rules that can achieve specific goals
- Understanding dependency chains
- Planning to achieve business objectives
- Checking if goals are achievable with current facts
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from symbolica import Engine, facts, goal

def main():
    print("Backward Chaining Example")
    print("=" * 50)
    
    # Load planning rules
    engine = Engine.from_file("planning.yaml")
    
    print("Business planning rules loaded")
    print(f"Total rules: {len(engine.rules)}")
    
    # Define our goal: achieve profitability
    profit_goal = goal(profitable=True)
    
    print(f"\nGoal: {profit_goal.target_facts}")
    
    # Find rules that can achieve this goal
    print("\nFinding rules that can achieve profitability...")
    supporting_rules = engine.find_rules_for_goal(profit_goal)
    
    print("Rules that can directly achieve the goal:")
    for rule in supporting_rules:
        print(f"  - {rule.id}: {rule.condition}")
    
    # Analyze what's needed for the main rule
    main_rule = supporting_rules[0] if supporting_rules else None
    if main_rule:
        print(f"\nAnalyzing requirements for '{main_rule.id}':")
        print(f"Condition: {main_rule.condition}")
        print("This requires: revenue > costs AND efficiency > 0.8")
    
    # Check different scenarios
    scenarios = [
        {
            "name": "Scenario 1: Well-funded startup",
            "facts": facts(
                budget=100000,
                tech_budget=30000,
                training_budget=8000,
                engineering_team=4,
                market_research=True,
                management_approval=True,
                current_headcount=25,
                time_allocation=50
            )
        },
        {
            "name": "Scenario 2: Limited budget company",
            "facts": facts(
                budget=30000,
                tech_budget=10000,
                training_budget=3000,
                engineering_team=2,
                market_research=False,
                management_approval=True,
                current_headcount=15,
                time_allocation=20
            )
        },
        {
            "name": "Scenario 3: Large established company",
            "facts": facts(
                budget=500000,
                tech_budget=100000,
                training_budget=25000,
                engineering_team=10,
                market_research=True,
                management_approval=True,
                current_headcount=100,
                time_allocation=80
            )
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}:")
        print("-" * 40)
        
        # Check if goal is achievable
        can_achieve = engine.can_achieve_goal(profit_goal, scenario['facts'])
        print(f"Can achieve profitability: {can_achieve}")
        
        # Show what actually fires
        result = engine.reason(scenario['facts'])
        print(f"Rules that fire: {result.fired_rules}")
        
        if result.verdict:
            print(f"Achieved results: {result.verdict}")
        
        # Analyze path to goal
        analyze_path_to_goal(engine, profit_goal, scenario['facts'])
    
    # Demonstrate goal analysis
    print(f"\nGoal Analysis:")
    analyze_goal_dependencies(engine, profit_goal)

def analyze_path_to_goal(engine, goal_obj, current_facts):
    """Analyze what steps are needed to achieve the goal."""
    # Find what we can achieve immediately
    result = engine.reason(current_facts)
    achieved_facts = result.verdict
    
    # Combine current and achieved facts
    all_facts = dict(current_facts)
    all_facts.update(achieved_facts)
    
    # Check if we can now achieve the goal
    can_achieve = engine.can_achieve_goal(goal_obj, all_facts)
    
    if can_achieve:
        print(f"  Path exists through fired rules: {result.fired_rules}")
    else:
        print(f"  Goal not achievable - missing requirements")
        
        # Find what's still needed
        supporting_rules = engine.find_rules_for_goal(goal_obj)
        if supporting_rules:
            main_rule = supporting_rules[0]
            print(f"  Main rule '{main_rule.id}' needs: {main_rule.condition}")

def analyze_goal_dependencies(engine, goal_obj):
    """Analyze the dependency chain for achieving a goal."""
    print("Goal dependency analysis:")
    
    supporting_rules = engine.find_rules_for_goal(goal_obj)
    print(f"Direct goal achievement rules: {len(supporting_rules)}")
    
    for rule in supporting_rules:
        print(f"  Rule: {rule.id}")
        print(f"    Condition: {rule.condition}")
        print(f"    Sets: {list(rule.actions.keys())}")
        
        # Look for rules that could satisfy this rule's conditions
        # This is a simplified dependency analysis
        condition_keywords = extract_keywords_from_condition(rule.condition)
        related_rules = find_rules_that_set(engine, condition_keywords)
        
        if related_rules:
            print(f"    Supported by rules that set: {condition_keywords}")
            for related_rule in related_rules[:3]:  # Show first 3
                print(f"      - {related_rule.id}: sets {list(related_rule.actions.keys())}")

def extract_keywords_from_condition(condition):
    """Extract potential variable names from condition string."""
    # Simple keyword extraction (would be more sophisticated in real implementation)
    keywords = []
    import re
    
    # Find variable-like patterns
    patterns = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', condition)
    
    # Filter out common operators and keep likely variable names
    operators = {'and', 'or', 'not', 'true', 'false', 'True', 'False'}
    keywords = [p for p in patterns if p not in operators and not p.replace('.', '').replace('-', '').isdigit()]
    
    return keywords

def find_rules_that_set(engine, keywords):
    """Find rules that set any of the given keywords in their actions."""
    matching_rules = []
    
    for rule in engine.rules:
        rule_sets = set(rule.actions.keys())
        if any(keyword in rule_sets for keyword in keywords):
            matching_rules.append(rule)
    
    return matching_rules

if __name__ == "__main__":
    main() 