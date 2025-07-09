#!/usr/bin/env python3
"""
LLM Augmented Rules Example
===========================

Demonstrates the new LLM integration capability in Symbolica.
Rules can now call prompt() to query LLMs for real-time data and decisions.
"""

from symbolica import Engine, facts
from symbolica._internal.llm_provider import MockLLMProvider, OpenAIProvider

# Example rules using LLM augmented prompts
llm_rules = """
rules:
  - id: "fraud_detection"
    priority: 100
    condition: "prompt('Population of United States') > customer_count"
    actions:
      fraud_check_passed: true
      population_verified: true
    tags: ["fraud", "llm"]
  
  - id: "market_sentiment_approval"
    priority: 90
    condition: "amount < 10000 and prompt('Is the sky blue') == 'true'"
    actions:
      sentiment_approved: true
      market_conditions: "favorable"
    tags: ["market", "llm"]
    
  - id: "dynamic_risk_assessment"
    priority: 80
    condition: "prompt('What is 2+2') == 4 and risk_score < 0.5"
    actions:
      dynamic_risk: "low"
      auto_approve: true
    tags: ["risk", "llm"]
    
  - id: "geographic_compliance"
    priority: 70
    condition: "country == 'FR' and prompt('Capital of France') == 'Paris'"
    actions:
      geo_compliant: true
      regulatory_check: "passed"
    tags: ["compliance", "geography", "llm"]
"""

def demo_llm_augmented_rules():
    """Demonstrate LLM augmented rules with mock provider."""
    print("=== LLM Augmented Rules Demo ===")
    
    # Create engine with mock LLM provider
    mock_provider = MockLLMProvider()
    engine = Engine.from_yaml(llm_rules, llm_provider=mock_provider)
    
    print("Available LLM providers:")
    for name, provider_type in engine.list_llm_providers().items():
        print(f"  {name}: {provider_type}")
    
    print("\nTest cases:")
    
    # Test case 1: Fraud detection scenario
    print("\n1. Fraud detection scenario:")
    case1 = facts(
        customer_count=100000000,  # 100M customers (less than US population)
        amount=5000,
        risk_score=0.3,
        country="US"
    )
    
    result1 = engine.reason(case1)
    print(f"Facts: {case1.data}")
    print(f"Verdict: {result1.verdict}")
    print(f"Rules fired: {result1.fired_rules}")
    print(f"Reasoning: {result1.reasoning}")
    
    # Test case 2: Normal operation
    print("\n2. Normal operation scenario:")
    case2 = facts(
        customer_count=100000,  # 100K customers (less than US population)
        amount=3000,
        risk_score=0.2,
        country="FR"
    )
    
    result2 = engine.reason(case2)
    print(f"Facts: {case2.data}")
    print(f"Verdict: {result2.verdict}")
    print(f"Rules fired: {result2.fired_rules}")
    print(f"Reasoning: {result2.reasoning}")
    
    # Show cache statistics
    print(f"\nLLM Cache Stats: {engine.get_llm_cache_stats()}")


def demo_llm_with_real_data():
    """Demonstrate more realistic LLM usage patterns."""
    print("\n=== Realistic LLM Data Demo ===")
    
    realistic_rules = """
rules:
  - id: "economic_indicator_check"
    priority: 100
    condition: "loan_amount > prompt('GDP of United States') / 1000000"
    actions:
      economic_review_required: true
      loan_tier: "institutional"
    
  - id: "knowledge_based_approval"
    priority: 90
    condition: "education_field == 'data science' and prompt('What is 2+2') == 4"
    actions:
      knowledge_verified: true
      fast_track: true
"""
    
    engine = Engine.from_yaml(realistic_rules)
    
    # Test with realistic loan scenario
    loan_facts = facts(
        loan_amount=50000000,  # 50M loan
        education_field="data science",
        applicant_type="corporation"
    )
    
    result = engine.reason(loan_facts)
    print(f"Loan application: {loan_facts.data}")
    print(f"Decision: {result.verdict}")
    print(f"Rules fired: {result.fired_rules}")
    print(f"Reasoning: {result.reasoning}")


def demo_llm_error_handling():
    """Demonstrate error handling in LLM calls."""
    print("\n=== LLM Error Handling Demo ===")
    
    error_rules = """
rules:
  - id: "llm_dependent_rule"
    condition: "prompt('This will cause an error in some LLMs') > 0"
    actions:
      llm_success: true
"""
    
    engine = Engine.from_yaml(error_rules)
    
    test_facts = facts(value=100)
    
    try:
        result = engine.reason(test_facts)
        print(f"Result: {result.verdict}")
        print(f"Rules fired: {result.fired_rules}")
    except Exception as e:
        print(f"Error handled: {e}")


def demo_llm_caching():
    """Demonstrate LLM response caching."""
    print("\n=== LLM Caching Demo ===")
    
    cache_rules = """
rules:
  - id: "cached_prompt_rule"
    condition: "prompt('Population of United States') > customer_base"
    actions:
      scale_check: "large_scale"
"""
    
    engine = Engine.from_yaml(cache_rules)
    
    # First call - should hit LLM
    print("First call (cache miss):")
    result1 = engine.reason(facts(customer_base=100000000))
    print(f"Cache stats: {engine.get_llm_cache_stats()}")
    
    # Second call - should use cache
    print("\nSecond call (cache hit):")
    result2 = engine.reason(facts(customer_base=200000000))
    print(f"Cache stats: {engine.get_llm_cache_stats()}")
    
    # Clear cache
    engine.clear_llm_cache()
    print(f"\nAfter cache clear: {engine.get_llm_cache_stats()}")


def demo_openai_integration():
    """Demonstrate OpenAI integration (requires API key)."""
    print("\n=== OpenAI Integration Demo ===")
    
    import os
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("OPENAI_API_KEY not found in environment. Skipping OpenAI demo.")
        return
    
    try:
        openai_provider = OpenAIProvider(api_key=api_key, model="gpt-3.5-turbo")
        
        simple_rules = """
rules:
  - id: "openai_test"
    condition: "prompt('What is 5+5?') == 10"
    actions:
      openai_working: true
"""
        
        engine = Engine.from_yaml(simple_rules, llm_provider=openai_provider)
        result = engine.reason(facts())
        
        print(f"OpenAI test result: {result.verdict}")
        print(f"Rules fired: {result.fired_rules}")
        
    except ImportError:
        print("OpenAI package not installed. Run: pip install openai")
    except Exception as e:
        print(f"OpenAI integration error: {e}")


if __name__ == "__main__":
    demo_llm_augmented_rules()
    demo_llm_with_real_data()
    demo_llm_error_handling()
    demo_llm_caching()
    demo_openai_integration()
    
    print("\n=== LLM Augmented Rules Demo Complete ===")
    print("✓ prompt() function in rule conditions")
    print("✓ Multiple LLM provider support")
    print("✓ Intelligent caching system")
    print("✓ Error handling and fallbacks")
    print("✓ Real-time data integration") 