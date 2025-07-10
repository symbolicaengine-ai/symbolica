#!/usr/bin/env python3
"""
Simple React-Style State Management Example
==========================================

Demonstrates React-style state flow where rules write intermediate facts
that other rules immediately use.

This shows the core concept working with simple computations.
"""

from symbolica import Engine, facts
import time


def main():
    # Simple rules with facts (intermediate state) and actions (final outputs)
    yaml_rules = """
    rules:
      # Stage 1: Calculate basic metrics
      - id: "calculate_metrics"
        priority: 100
        condition: "True"
        facts:
          score_doubled: score * 2
          is_high_score: score > 80
          bonus_eligible: score > 75
        actions:
          metrics_calculated: true
      
      # Stage 2: Use Stage 1 facts for decisions
      - id: "high_score_bonus"
        priority: 90
        condition: "is_high_score and bonus_eligible"
        facts:
          bonus_amount: score_doubled * 0.1
          bonus_type: "performance"
        actions:
          bonus_awarded: true
          
      - id: "standard_processing"
        priority: 89
        condition: "not is_high_score"
        facts:
          bonus_amount: 10
          bonus_type: "participation"
        actions:
          standard_bonus: true
      
      # Stage 3: Final calculation using all previous facts
      - id: "final_calculation"
        priority: 80
        condition: "bonus_amount is not None"
        actions:
          final_bonus: bonus_amount
          bonus_category: bonus_type
    """
    
    engine = Engine.from_yaml(yaml_rules)
    
    print("🎯 Simple React-Style State Management")
    print("=" * 45)
    print()
    
    # Test Case 1: High Score
    print("Test Case 1: High Score (score=85)")
    print("-" * 35)
    
    high_score_facts = facts(score=85)
    result1 = engine.reason(high_score_facts)
    
    print("📊 Intermediate Facts (React-style state):")
    for key, value in result1.intermediate_facts.items():
        print(f"  {key}: {value}")
    print()
    
    print("✅ Final Actions:")
    for key, value in result1.verdict.items():
        print(f"  {key}: {value}")
    print()
    print()
    
    # Test Case 2: Low Score
    print("Test Case 2: Low Score (score=60)")
    print("-" * 34)
    
    low_score_facts = facts(score=60)
    result2 = engine.reason(low_score_facts)
    
    print("📊 Intermediate Facts (React-style state):")
    for key, value in result2.intermediate_facts.items():
        print(f"  {key}: {value}")
    print()
    
    print("✅ Final Actions:")
    for key, value in result2.verdict.items():
        print(f"  {key}: {value}")
    print()
    print()
    
    print("🧬 State Flow Analysis")
    print("=" * 25)
    print("Stage 1: Calculate metrics → creates score_doubled, is_high_score, bonus_eligible")
    print("Stage 2: Use Stage 1 facts in conditions → creates bonus_amount, bonus_type") 
    print("Stage 3: Use Stage 2 facts → creates final outputs")
    print()
    print("🚀 This demonstrates React-style reactive state updates!")
    print("   Facts from early rules become immediately available to later rules")


if __name__ == "__main__":
    main() 