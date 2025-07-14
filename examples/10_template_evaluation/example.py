#!/usr/bin/env python3
"""
Template Evaluation Example

This example demonstrates Symbolica's template evaluation capabilities through
a real-world employee performance review scenario.

Template features showcased:
- Variable substitution: {{ variable_name }}
- Mathematical expressions: {{ value1 + value2 }}
- Conditional expressions: {{ 'result' if condition else 'alternative' }}
- Function calls: {{ min(value, 100) }}
- Complex nested expressions

Run this example to see how templates can generate dynamic content
based on data and business logic.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from symbolica import Engine, facts


def main():
    """
    Demonstrate template evaluation with employee performance review
    """
    print("Symbolica Template Evaluation Example")
    print("=" * 50)
    print()
    
    # Initialize the Symbolica engine
    engine = Engine.from_file("business_templates.yaml")
    
    print("Loaded template evaluation rules")
    print("Demonstrating dynamic template generation...")
    print()
    
    # Test Case 1: High performer
    print("Test Case 1: High Performer")
    print("=" * 30)
    
    high_performer = facts(
        employee_id="EMP001",
        employee_name="Sarah Johnson",
        department="Sales",
        review_period="Q4 2024",
        sales_target=120000,
        sales_achieved=145000,
        quality_score=88,
        teamwork_score=92
    )
    
    print(f"Employee: {high_performer.data['employee_name']}")
    print(f"Sales: ${high_performer.data['sales_achieved']:,} / ${high_performer.data['sales_target']:,} ({high_performer.data['sales_achieved']/high_performer.data['sales_target']*100:.1f}%)")
    
    result = engine.reason(high_performer)
    
    if result and result.verdict and 'performance_report' in result.verdict:
        print("\nGenerated Performance Review:")
        print("-" * 40)
        print(result.verdict['performance_report'])
    
    # Test Case 2: Average performer
    print("\n" + "=" * 60)
    print("Test Case 2: Average Performer")
    print("=" * 30)
    
    average_performer = facts(
        employee_id="EMP002",
        employee_name="Mike Chen",
        department="Sales",
        review_period="Q4 2024",
        sales_target=100000,
        sales_achieved=95000,
        quality_score=75,
        teamwork_score=80
    )
    
    print(f"Employee: {average_performer.data['employee_name']}")
    print(f"Sales: ${average_performer.data['sales_achieved']:,} / ${average_performer.data['sales_target']:,} ({average_performer.data['sales_achieved']/average_performer.data['sales_target']*100:.1f}%)")
    
    result = engine.reason(average_performer)
    
    if result and result.verdict and 'performance_report' in result.verdict:
        print("\nGenerated Performance Review:")
        print("-" * 40)
        print(result.verdict['performance_report'])
    
    # Test Case 3: Below expectations
    print("\n" + "=" * 60)
    print("Test Case 3: Below Expectations")
    print("=" * 30)
    
    low_performer = facts(
        employee_id="EMP003",
        employee_name="Alex Turner",
        department="Sales",
        review_period="Q4 2024",
        sales_target=80000,
        sales_achieved=55000,
        quality_score=60,
        teamwork_score=65
    )
    
    print(f"Employee: {low_performer.data['employee_name']}")
    print(f"Sales: ${low_performer.data['sales_achieved']:,} / ${low_performer.data['sales_target']:,} ({low_performer.data['sales_achieved']/low_performer.data['sales_target']*100:.1f}%)")
    
    result = engine.reason(low_performer)
    
    if result and result.verdict and 'performance_report' in result.verdict:
        print("\nGenerated Performance Review:")
        print("-" * 40)
        print(result.verdict['performance_report'])
    
    print("\n" + "=" * 60)
    print("Template Features Demonstrated:")
    print("✓ Variable substitution: employee name, ID, department")
    print("✓ Mathematical expressions: sales calculations, scoring averages")
    print("✓ Conditional logic: performance ratings based on metrics")
    print("✓ Dynamic recommendations: based on calculated scores")
    print("✓ Complex nested expressions: multi-level conditional logic")
    print("✓ Formatted output: professional business document structure")


if __name__ == "__main__":
    main() 