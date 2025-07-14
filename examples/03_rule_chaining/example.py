#!/usr/bin/env python3
"""
Rule Chaining Example
====================

This example demonstrates how rules can trigger other rules to create workflows:
- Using triggers to chain rules together
- Building multi-step processes
- Understanding execution order with priorities
- Creating complex business workflows
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from symbolica import Engine, facts

def main():
    print("Rule Chaining Example")
    print("=" * 50)
    
    # Load workflow rules
    engine = Engine.from_file("workflow.yaml")
    
    print("Workflow rules loaded:")
    for rule in engine.rules:
        triggers = f" -> {rule.triggers}" if rule.triggers else ""
        print(f"  - {rule.id} (priority {rule.priority}){triggers}")
    
    # Test case 1: VIP customer workflow
    print("\nTest 1: VIP Customer Workflow")
    vip_customer = facts(
        customer_tier="vip",
        credit_score=800,
        annual_income=120000
    )
    
    result = engine.reason(vip_customer)
    print(f"Input: {vip_customer.data}")
    print(f"Final result: {result.verdict}")
    print(f"Rules fired: {result.fired_rules}")
    print("\nStep-by-step workflow:")
    parse_workflow_steps(result.reasoning)
    
    # Show priority insights for complex cases
    if len(result.fired_rules) != len(result.get_winning_rules()):
        print(f"\nPriority Resolution: {len(result.fired_rules)} rules fired, {len(result.get_winning_rules())} contributed to final verdict")
        print("Use result.explain_with_priorities() to see what was overridden")
    
    # Test case 2: Standard customer workflow
    print("\nTest 2: Standard Customer Workflow")
    standard_customer = facts(
        customer_tier="standard",
        credit_score=680,
        annual_income=60000
    )
    
    result = engine.reason(standard_customer)
    print(f"Input: {standard_customer.data}")
    print(f"Final result: {result.verdict}")
    print(f"Rules fired: {result.fired_rules}")
    print("\nStep-by-step workflow:")
    parse_workflow_steps(result.reasoning)
    
    # Show priority insights for complex cases
    if len(result.fired_rules) != len(result.get_winning_rules()):
        print(f"\nPriority Resolution: {len(result.fired_rules)} rules fired, {len(result.get_winning_rules())} contributed to final verdict")
        print("Use result.explain_with_priorities() to see what was overridden")
    
    # Test case 3: Rejected customer (no workflow)
    print("\nTest 3: Rejected Customer (No Workflow)")
    rejected_customer = facts(
        customer_tier="standard",
        credit_score=550,
        annual_income=30000
    )
    
    result = engine.reason(rejected_customer)
    print(f"Input: {rejected_customer.data}")
    print(f"Final result: {result.verdict}")
    print(f"Rules fired: {result.fired_rules}")
    if not result.fired_rules:
        print("No workflow triggered - customer doesn't meet approval criteria")
    
    # Demonstrate workflow analysis
    print("\nWorkflow Analysis:")
    analyze_workflow_paths(engine)

def parse_workflow_steps(reasoning):
    """Parse and display workflow steps from reasoning."""
    lines = reasoning.split('\n')
    step = 1
    for line in lines:
        line = line.strip()
        if line and ':' in line:
            # Extract rule name and details
            rule_name = line.split(':')[0].strip()
            rule_details = ':'.join(line.split(':')[1:]).strip()
            
            if 'triggered by' in rule_details:
                # Extract the triggered by information
                main_part = rule_details.split('(triggered by')[0].strip()
                trigger_part = rule_details.split('(triggered by')[1].strip(')')
                print(f"  Step {step}: {rule_name} - {main_part} (triggered by {trigger_part})")
            else:
                # Initial rule (not triggered by another)
                print(f"  Step {step}: {rule_name} - {rule_details}")
            step += 1

def analyze_workflow_paths(engine):
    """Analyze possible workflow paths."""
    print("Possible workflow paths:")
    
    # Find trigger relationships
    trigger_map = {}
    for rule in engine.rules:
        if rule.triggers:
            trigger_map[rule.id] = rule.triggers
    
    # VIP path
    print("  VIP path: vip_approval -> vip_welcome + assign_banker")
    if 'vip_approval' in trigger_map:
        for trigger in trigger_map['vip_approval']:
            print(f"    -> {trigger}")
            if trigger in trigger_map:
                for sub_trigger in trigger_map[trigger]:
                    print(f"      -> {sub_trigger}")
    
    # Standard path
    print("  Standard path: standard_approval -> standard_welcome + setup_account")
    if 'standard_approval' in trigger_map:
        for trigger in trigger_map['standard_approval']:
            print(f"    -> {trigger}")
            if trigger in trigger_map:
                for sub_trigger in trigger_map[trigger]:
                    print(f"      -> {sub_trigger}")

if __name__ == "__main__":
    main() 