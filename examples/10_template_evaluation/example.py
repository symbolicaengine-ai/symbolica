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
    print("Demonstrating employee performance review template")
    print()
    
    # Employee performance data
    employee_facts = facts(
        employee_id="EMP001",
        employee_name="Sarah Johnson",
        department="Sales",
        review_period="Q4 2024",
        sales_target=120000,
        sales_achieved=145000,
        quality_score=88,
        teamwork_score=92
    )
    
    print(f"Processing performance review for: {employee_facts.data['employee_name']}")
    print(f"Sales Achievement: ${employee_facts.data['sales_achieved']:,} / ${employee_facts.data['sales_target']:,}")
    print()
    
    # Execute the template evaluation
    result = engine.reason(employee_facts)
    
    if result and result.verdict:
        print("Generated Performance Review:")
        print("-" * 40)
        print(result.verdict)
    else:
        print("No template generated - check rule conditions")
    
    print()
    print("Template Features Demonstrated:")
    print("- Variable substitution: employee name, ID, department")
    print("- Mathematical expressions: sales calculations, scoring averages")
    print("- Conditional logic: performance ratings based on metrics")
    print("- Function calls: min() for score capping")
    print("- Complex nested expressions: multi-level conditional logic")


if __name__ == "__main__":
    main() 