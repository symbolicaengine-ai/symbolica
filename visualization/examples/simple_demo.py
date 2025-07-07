#!/usr/bin/env python3
"""
Simple Demo - Quick Rule Visualization
=======================================

This demonstrates the simplest way to visualize your Symbolica rules.
Perfect for quick analysis during development.
"""

import sys
import os

# Add symbolica to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from symbolica import Engine
from visualization import RuleVisualizer


def quick_analysis():
    """Quick analysis of a simple rule set."""
    
    yaml_rules = """
rules:
  - id: age_check
    priority: 100
    condition: age >= 21
    actions:
      adult: true
      can_drink: true
    tags: [age]
  
  - id: income_check
    priority: 90
    condition: income > 40000
    actions:
      high_earner: true
    tags: [income]
  
  - id: credit_check
    priority: 80
    condition: adult and high_earner and credit_score > 650
    actions:
      loan_approved: true
      interest_rate: 3.5
    tags: [loan]
"""
    
    print("🔍 Quick Rule Visualization Demo")
    print("=" * 40)
    
    # Step 1: Load rules
    engine = Engine.from_yaml(yaml_rules)
    visualizer = RuleVisualizer(engine)
    
    # Step 2: Quick summary
    print("\n📊 SUMMARY")
    visualizer.quick_summary()
    
    # Step 3: Show execution order
    print("\n🔄 EXECUTION ORDER")
    print("-" * 20)
    summary = visualizer.get_execution_summary()
    for i, level in enumerate(summary['execution_levels']):
        print(f"Level {i}: {level}")
    
    # Step 4: Show AST for most complex rule
    print("\n🌳 AST STRUCTURE")
    print("-" * 20)
    visualizer.show_ast("credit_check")
    
    # Step 5: Generate report
    print("\n📄 GENERATING REPORT")
    print("-" * 20)
    visualizer.generate_report('quick_demo.html')
    print("✅ Report saved as: quick_demo.html")
    
    print("\n✨ Analysis complete! Open quick_demo.html in your browser to see the full report.")


def analyze_from_file():
    """Show how to analyze rules from a file."""
    
    # Create a sample YAML file
    sample_yaml = """
rules:
  - id: user_validation
    priority: 1000
    condition: email and user_id
    actions:
      valid_user: true
    tags: [validation]
  
  - id: permission_check
    priority: 900
    condition: valid_user and role in ['admin', 'user']
    actions:
      has_permission: true
    tags: [auth]
  
  - id: feature_access
    priority: 800
    condition: has_permission and subscription_active
    actions:
      can_access_features: true
    tags: [features]
"""
    
    # Save to file
    with open('sample_rules.yaml', 'w') as f:
        f.write(sample_yaml)
    
    print("\n🗂️  ANALYZING FROM FILE")
    print("=" * 40)
    
    # Load from file
    engine = Engine.from_file('sample_rules.yaml')
    visualizer = RuleVisualizer(engine)
    
    # Quick analysis
    print("\n📈 FILE ANALYSIS SUMMARY:")
    stats = visualizer.get_execution_summary()['statistics']
    print(f"   Rules: {stats['total_rules']}")
    print(f"   Levels: {stats['execution_levels']}")
    print(f"   Dependencies: {stats['total_dependencies']}")
    
    # Clean up
    os.remove('sample_rules.yaml')
    print("\n✅ File analysis complete!")


def main():
    """Run all demos."""
    quick_analysis()
    analyze_from_file()
    
    print("\n" + "=" * 50)
    print("🎉 Demo Complete!")
    print("\nNext steps:")
    print("1. Open the generated HTML reports in your browser")
    print("2. Try with your own YAML files using Engine.from_file()")
    print("3. Use RuleVisualizer in your own scripts")
    print("\nFor more examples, check:")
    print("- basic_visualization.py")
    print("- advanced_analysis.py")


if __name__ == "__main__":
    main() 