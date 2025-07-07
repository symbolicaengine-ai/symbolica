#!/usr/bin/env python3
"""
Basic Visualization Example
===========================

This example demonstrates how to use the Symbolica rule visualization tools
to analyze rule structure, dependencies, and execution order.
"""

import sys
import os

# Add symbolica to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from symbolica import Engine
from visualization import RuleVisualizer


def main():
    """Demonstrate basic visualization functionality."""
    
    # Sample YAML rules for demonstration
    yaml_content = """
rules:
  - id: check_age
    priority: 100
    condition: age >= 18
    actions:
      is_adult: true
    tags: [age, validation]
  
  - id: check_income
    priority: 90
    condition: income > 50000
    actions:
      high_income: true
    tags: [income, validation]
  
  - id: loan_eligibility
    priority: 80
    condition: is_adult and high_income
    actions:
      loan_eligible: true
    tags: [loan, decision]
  
  - id: premium_user
    priority: 70
    condition: loan_eligible and income > 100000
    actions:
      premium_status: true
    tags: [premium, status]
"""
    
    print("Symbolica Rule Visualization Example")
    print("=" * 50)
    
    # Create engine and visualizer
    engine = Engine.from_yaml(yaml_content)
    visualizer = RuleVisualizer(engine)
    
    # 1. Quick summary
    print("\n1. QUICK SUMMARY")
    print("-" * 30)
    visualizer.quick_summary()
    
    # 2. Show AST for specific rule
    print("\n2. AST VISUALIZATION")
    print("-" * 30)
    visualizer.show_ast("loan_eligibility")
    
    # 3. Show dependency analysis
    print("\n3. DEPENDENCY ANALYSIS")
    print("-" * 30)
    visualizer.show_dag()
    
    # 4. Analyze specific rule
    print("\n4. DETAILED RULE ANALYSIS")
    print("-" * 30)
    analysis = visualizer.analyze_rule("loan_eligibility")
    print(f"Rule: {analysis['rule']['id']}")
    print(f"Condition fields: {analysis['condition_fields']}")
    print(f"Action fields: {analysis['action_fields']}")
    print(f"Dependencies: {analysis['dependencies'].get('dependencies', [])}")
    
    # 5. Generate reports
    print("\n5. GENERATING REPORTS")
    print("-" * 30)
    
    # HTML report
    visualizer.generate_report('rule_analysis_demo.html')
    
    # JSON export
    visualizer.export_json('rule_analysis_demo.json')
    
    # Graphviz export
    visualizer.export_graphviz('rule_dependencies_demo.dot')
    
    print("\nVisualization complete!")
    print("Generated files:")
    print("- rule_analysis_demo.html (comprehensive HTML report)")
    print("- rule_analysis_demo.json (analysis data)")
    print("- rule_dependencies_demo.dot (Graphviz dependency graph)")
    print("\nTo render the dependency graph:")
    print("dot -Tpng rule_dependencies_demo.dot -o dependencies.png")


if __name__ == "__main__":
    main() 