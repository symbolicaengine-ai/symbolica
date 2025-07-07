#!/usr/bin/env python3
"""
Advanced Rule Analysis Example
==============================

This example demonstrates advanced visualization features for complex rule sets
with multiple dependencies, conditional chains, and parallelization analysis.
"""

import sys
import os

# Add symbolica to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from symbolica import Engine
from visualization import RuleVisualizer


def create_complex_rule_set():
    """Create a complex rule set for demonstration."""
    return """
rules:
  # Data validation layer (highest priority)
  - id: validate_user_data
    priority: 1000
    condition: user_id and email
    actions:
      data_valid: true
    tags: [validation, data]
  
  - id: validate_financial_data
    priority: 999
    condition: income and credit_score
    actions:
      financial_data_valid: true
    tags: [validation, financial]
  
  # Risk assessment layer
  - id: basic_risk_check
    priority: 900
    condition: data_valid and age >= 18
    actions:
      basic_risk_passed: true
    tags: [risk, basic]
  
  - id: financial_risk_check
    priority: 890
    condition: financial_data_valid and credit_score >= 600
    actions:
      financial_risk_passed: true
    tags: [risk, financial]
  
  - id: employment_risk_check
    priority: 880
    condition: employment_status in ['employed', 'self_employed'] and income > 30000
    actions:
      employment_risk_passed: true
    tags: [risk, employment]
  
  # Product eligibility layer
  - id: basic_loan_eligibility
    priority: 800
    condition: basic_risk_passed and financial_risk_passed
    actions:
      basic_loan_eligible: true
    tags: [loan, basic]
  
  - id: premium_loan_eligibility
    priority: 790
    condition: basic_loan_eligible and employment_risk_passed and income > 80000
    actions:
      premium_loan_eligible: true
    tags: [loan, premium]
  
  - id: mortgage_eligibility
    priority: 780
    condition: premium_loan_eligible and credit_score >= 750 and income > 100000
    actions:
      mortgage_eligible: true
    tags: [mortgage, premium]
  
  # Parallel business rules (same priority - can execute in parallel)
  - id: loyalty_program_bronze
    priority: 700
    condition: basic_loan_eligible and customer_tenure >= 12
    actions:
      loyalty_bronze: true
    tags: [loyalty, bronze]
  
  - id: loyalty_program_silver
    priority: 700
    condition: premium_loan_eligible and customer_tenure >= 24
    actions:
      loyalty_silver: true
    tags: [loyalty, silver]
  
  - id: loyalty_program_gold
    priority: 700
    condition: mortgage_eligible and customer_tenure >= 36
    actions:
      loyalty_gold: true
    tags: [loyalty, gold]
  
  # Special offers (independent rules)
  - id: student_discount
    priority: 600
    condition: age <= 25 and student_status
    actions:
      student_discount_eligible: true
    tags: [discount, student]
  
  - id: senior_discount
    priority: 600
    condition: age >= 65
    actions:
      senior_discount_eligible: true
    tags: [discount, senior]
  
  # Final decision layer
  - id: final_offer_calculation
    priority: 500
    condition: basic_loan_eligible or premium_loan_eligible or mortgage_eligible
    actions:
      offer_ready: true
    tags: [final, offer]
"""


def analyze_complex_rules():
    """Analyze the complex rule set."""
    print("Complex Rule Analysis")
    print("=" * 50)
    
    # Create engine and visualizer
    yaml_content = create_complex_rule_set()
    engine = Engine.from_yaml(yaml_content)
    visualizer = RuleVisualizer(engine)
    
    # 1. Overall statistics
    print("\n1. RULE SET STATISTICS")
    print("-" * 30)
    visualizer.quick_summary()
    
    # 2. Execution order analysis
    print("\n2. EXECUTION ORDER ANALYSIS")
    print("-" * 30)
    summary = visualizer.get_execution_summary()
    
    print("Execution levels breakdown:")
    for i, level in enumerate(summary['execution_levels']):
        print(f"  Level {i}: {len(level)} rules - {level}")
    
    print(f"\nParallelization opportunities:")
    for opp in summary['parallelization_opportunities']:
        print(f"  Level {opp['level']}: {opp['parallel_rules']} rules can run in parallel")
    
    # 3. Critical path analysis
    print("\n3. CRITICAL PATH ANALYSIS")
    print("-" * 30)
    critical_path = summary['critical_path']
    if critical_path:
        print("Critical path (longest dependency chain):")
        for i, rule_id in enumerate(critical_path):
            arrow = " → " if i < len(critical_path) - 1 else ""
            print(f"  {rule_id}{arrow}")
        print(f"Total length: {len(critical_path)} rules")
    else:
        print("No critical path found - rules are independent")
    
    # 4. Dependency analysis by tags
    print("\n4. DEPENDENCY ANALYSIS BY TAGS")
    print("-" * 30)
    
    tag_groups = {}
    for rule in engine.rules:
        tags = getattr(rule, 'tags', [])
        for tag in tags:
            if tag not in tag_groups:
                tag_groups[tag] = []
            tag_groups[tag].append(rule.id)
    
    for tag, rules in sorted(tag_groups.items()):
        print(f"  {tag}: {len(rules)} rules - {rules}")
    
    # 5. Analyze specific complex rules
    print("\n5. DETAILED ANALYSIS OF KEY RULES")
    print("-" * 30)
    
    key_rules = ['mortgage_eligibility', 'final_offer_calculation', 'loyalty_program_gold']
    
    for rule_id in key_rules:
        analysis = visualizer.analyze_rule(rule_id)
        if 'error' not in analysis:
            rule_info = analysis['rule']
            deps = analysis['dependencies']
            
            print(f"\nRule: {rule_id}")
            print(f"  Priority: {rule_info['priority']}")
            print(f"  Condition: {rule_info['condition']}")
            print(f"  Fields used: {analysis['condition_fields']}")
            print(f"  Fields set: {analysis['action_fields']}")
            print(f"  Dependencies: {deps.get('dependencies', [])}")
            print(f"  Required by: {deps.get('dependents', [])}")
            print(f"  Execution level: {deps.get('level', 'unknown')}")
    
    # 6. Performance implications
    print("\n6. PERFORMANCE IMPLICATIONS")
    print("-" * 30)
    
    stats = summary['statistics']
    print(f"Total rules: {stats['total_rules']}")
    print(f"Execution levels: {stats['execution_levels']}")
    print(f"Maximum parallelism: {max(len(level) for level in summary['execution_levels']) if summary['execution_levels'] else 0} rules")
    print(f"Sequential bottlenecks: {sum(1 for level in summary['execution_levels'] if len(level) == 1)}")
    print(f"Critical path length: {stats['critical_path_length']} rules")
    
    efficiency = (stats['total_rules'] / stats['execution_levels']) if stats['execution_levels'] > 0 else 0
    print(f"Parallelization efficiency: {efficiency:.1f} rules per level (higher is better)")
    
    # 7. Generate comprehensive report
    print("\n7. GENERATING COMPREHENSIVE REPORT")
    print("-" * 30)
    
    visualizer.generate_report('advanced_rule_analysis.html')
    visualizer.export_json('advanced_rule_analysis.json')
    visualizer.export_graphviz('advanced_dependencies.dot')
    
    print("Advanced analysis complete!")
    print("Generated files:")
    print("- advanced_rule_analysis.html")
    print("- advanced_rule_analysis.json") 
    print("- advanced_dependencies.dot")


def demonstrate_ast_analysis():
    """Demonstrate AST analysis for complex conditions."""
    print("\n" + "=" * 50)
    print("AST ANALYSIS DEMONSTRATION")
    print("=" * 50)
    
    # Complex conditions for AST analysis
    complex_yaml = """
rules:
  - id: complex_condition_1
    priority: 100
    condition: (age >= 18 and age <= 65) and (income > 50000 or assets > 100000)
    actions:
      complex_eligible: true
  
  - id: complex_condition_2
    priority: 90
    condition: credit_score >= 700 and employment_status in ['employed', 'self_employed'] and not bankruptcy_history
    actions:
      prime_customer: true
  
  - id: nested_logic
    priority: 80
    condition: (region in ['NY', 'CA', 'TX']) and ((income > 75000 and credit_score > 650) or (assets > 200000))
    actions:
      premium_region_eligible: true
"""
    
    engine = Engine.from_yaml(complex_yaml)
    visualizer = RuleVisualizer(engine)
    
    print("\nAST structures for complex conditions:")
    print("-" * 40)
    
    for rule in engine.rules:
        print(f"\nRule: {rule.id}")
        print(f"Condition: {rule.condition}")
        ast_tree = visualizer.ast_viz.get_ast_tree(rule.id)
        if ast_tree:
            print("AST Structure:")
            print(visualizer.ast_viz.to_text_tree(ast_tree))


if __name__ == "__main__":
    analyze_complex_rules()
    demonstrate_ast_analysis() 