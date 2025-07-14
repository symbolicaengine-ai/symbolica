#!/usr/bin/env python3
"""
Engine-Level Fallback Example
=============================

This example demonstrates the new engine-level fallback functionality:
- Strict mode: Fails on evaluation errors (default)
- Auto mode: Tries structured evaluation first, falls back to LLM on errors
- Fallback statistics and performance tracking

Setup:
pip install openai
export OPENAI_API_KEY="your-api-key-here"
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from symbolica import Engine, facts

def main():
    print("Engine-Level Fallback Example")
    print("=" * 50)
    
    # Check for OpenAI API key (optional for this demo)
    api_key = os.getenv('OPENAI_API_KEY')
    
    # Test rules with both clean and problematic conditions
    rules_yaml = """
rules:
  - id: clean_rule
    priority: 100
    condition: "credit_score > 700 and annual_income > 50000"
    actions:
      approved: true
      reason: "Excellent credit and income"
      
  - id: missing_data_rule
    priority: 90
    condition: "missing_field > 1000"  # This field doesn't exist
    actions:
      special_approval: true
      reason: "Special case handling"
      
  - id: complex_condition
    priority: 80
    condition: "customer_tier == 'vip' and undefined_metric > threshold"
    actions:
      vip_benefits: true
      reason: "VIP customer benefits"
"""
    
    customer_data = facts(
        credit_score=750,
        annual_income=80000,
        customer_tier="vip"
        # Note: missing_field and undefined_metric are not provided
    )
    
    print("Customer data:", customer_data.data)
    print()
    
    # Test 1: Strict mode (default behavior)
    print("Test 1: Strict Mode (default)")
    print("-" * 30)
    engine_strict = Engine.from_yaml(rules_yaml, fallback_strategy="strict")
    result_strict = engine_strict.reason(customer_data)
    
    print(f"Rules fired: {result_strict.fired_rules}")
    print(f"Evaluation method: {result_strict.evaluation_method}")
    print(f"Fallback triggered: {result_strict.fallback_triggered}")
    print(f"Verdict: {result_strict.verdict}")
    print(f"Execution time: {result_strict.execution_time_ms:.2f}ms")
    print()
    
    # Test 2: Auto mode without LLM (falls back to strict)
    print("Test 2: Auto Mode without LLM")
    print("-" * 30)
    engine_auto_no_llm = Engine.from_yaml(rules_yaml, fallback_strategy="auto")
    result_auto_no_llm = engine_auto_no_llm.reason(customer_data)
    
    print(f"Rules fired: {result_auto_no_llm.fired_rules}")
    print(f"Evaluation method: {result_auto_no_llm.evaluation_method}")
    print(f"Fallback triggered: {result_auto_no_llm.fallback_triggered}")
    print(f"Verdict: {result_auto_no_llm.verdict}")
    print()
    
    # Test 3: Auto mode with LLM (if available)
    if api_key:
        print("Test 3: Auto Mode with LLM")
        print("-" * 30)
        
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            
            engine_auto_llm = Engine.from_yaml(
                rules_yaml, 
                fallback_strategy="auto", 
                llm_client=client
            )
            result_auto_llm = engine_auto_llm.reason(customer_data)
            
            print(f"Rules fired: {result_auto_llm.fired_rules}")
            print(f"Evaluation method: {result_auto_llm.evaluation_method}")
            print(f"Fallback triggered: {result_auto_llm.fallback_triggered}")
            print(f"Verdict: {result_auto_llm.verdict}")
            print(f"Execution time: {result_auto_llm.execution_time_ms:.2f}ms")
            
            # Show detailed fallback statistics
            stats = result_auto_llm.fallback_stats
            print()
            print("Fallback Statistics:")
            print(f"  Total evaluations: {stats['total_evaluations']}")
            print(f"  Structured success rate: {stats['structured_success_rate']:.1%}")
            print(f"  LLM fallback rate: {stats['llm_fallback_rate']:.1%}")
            print(f"  Error rate: {stats['error_rate']:.1%}")
            
            if stats['fallback_reasons']:
                print("  Fallback reasons:")
                for reason in stats['fallback_reasons']:
                    print(f"    {reason['rule_id']}: {reason['reason']}")
            
        except ImportError:
            print("OpenAI library not installed. Run: pip install openai")
        except Exception as e:
            print(f"Error with LLM integration: {e}")
    else:
        print("Test 3: Auto Mode with LLM")
        print("-" * 30)
        print("Set OPENAI_API_KEY environment variable to test LLM fallback")
    
    print()
    print("Summary:")
    print("- Strict mode: Only rules with valid conditions fire")
    print("- Auto mode: Intelligently falls back to LLM for problematic conditions")
    print("- Fallback statistics: Track performance and success rates")
    print("- No breaking changes: Existing code works with strict mode by default")

if __name__ == "__main__":
    main() 