#!/usr/bin/env python3
"""
LLM Integration Example
======================

This example demonstrates LLM integration with Symbolica:
- Using PROMPT() function in rule conditions
- Type conversion (str, int, bool, float)
- Hybrid AI-rule decision making
- Secure prompt handling with OpenAI API

Setup:
pip install openai
export OPENAI_API_KEY="your-api-key-here"
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from symbolica import Engine, facts

def main():
    print("LLM Integration Example")
    print("=" * 50)
    
    # Check for OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: Please set your OPENAI_API_KEY environment variable")
        print("Example: export OPENAI_API_KEY='your-api-key-here'")
        return
    
    # Import and create OpenAI client
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        print("OpenAI client initialized successfully")
    except ImportError:
        print("Error: Please install the OpenAI library: pip install openai")
        return
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        return
    
    # Load rules with LLM integration
    engine = Engine.from_file("customer_service.yaml", llm_client=client)
    
    print("Customer service rules with LLM integration loaded")
    print("PROMPT() functions will be evaluated using OpenAI API")
    
    # Test case 1: Angry customer
    print("\nTest 1: Angry Customer")
    angry_message = facts(
        message="This is absolutely terrible! Your service is the worst and I hate everything about it!"
    )
    
    print(f"Message: {angry_message['message']}")
    print("Processing with AI analysis...")
    
    result = engine.reason(angry_message)
    print(f"Result: {result.verdict}")
    print(f"Fired rules: {result.fired_rules}")
    print(f"AI Analysis: {result.reasoning}")
    
    # Test case 2: Technical issue
    print("\nTest 2: Technical Issue")
    tech_message = facts(
        message="The server keeps crashing and I'm getting error 500 when I try to login. This is a critical bug."
    )
    
    print(f"Message: {tech_message['message']}")
    print("Processing with AI analysis...")
    
    result = engine.reason(tech_message)
    print(f"Result: {result.verdict}")
    print(f"Fired rules: {result.fired_rules}")
    
    # Test case 3: Billing inquiry
    print("\nTest 3: Billing Inquiry")
    billing_message = facts(
        message="I have a question about my invoice and need a refund for the overcharge on my last bill."
    )
    
    print(f"Message: {billing_message['message']}")
    print("Processing with AI analysis...")
    
    result = engine.reason(billing_message)
    print(f"Result: {result.verdict}")
    print(f"Fired rules: {result.fired_rules}")
    
    # Test case 4: Urgent positive feedback
    print("\nTest 4: Urgent Positive Feedback")
    urgent_positive = facts(
        message="I absolutely love your product! This is urgent - please contact me immediately for a major partnership opportunity worth millions."
    )
    
    print(f"Message: {urgent_positive['message']}")
    print("Processing with AI analysis...")
    
    result = engine.reason(urgent_positive)
    print(f"Result: {result.verdict}")
    print(f"Fired rules: {result.fired_rules}")
    
    # Test case 5: Low satisfaction
    print("\nTest 5: Low Satisfaction")
    low_satisfaction = facts(
        message="This experience has been awful, I'm extremely disappointed with everything. Worst service ever."
    )
    
    print(f"Message: {low_satisfaction['message']}")
    print("Processing with AI analysis...")
    
    result = engine.reason(low_satisfaction)
    print(f"Result: {result.verdict}")
    print(f"Fired rules: {result.fired_rules}")
    
    # Show capabilities
    print(f"\nPROMPT() Function Capabilities Demonstrated:")
    print("- String return: PROMPT('Analyze emotion in: {message}')")
    print("- Boolean return: PROMPT('Is this a technical issue: {message}', 'bool')")
    print("- Integer return: PROMPT('Rate urgency 1-10: {message}', 'int')")
    print("- Automatic security hardening and input sanitization")
    print("- Real-time AI analysis with OpenAI GPT models")

if __name__ == "__main__":
    main() 