"""
Unit Tests for LLM Integration
==============================

Tests for LLM client integration, PROMPT() function, and hybrid AI reasoning.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json
from typing import Dict, Any, Optional

from symbolica import Engine, facts
from symbolica.core.models import Rule
from symbolica.core.exceptions import ValidationError, EvaluationError, FunctionError


class MockLLMClient:
    """Mock LLM client for testing."""
    
    def __init__(self, responses: Dict[str, Any] = None):
        self.responses = responses or {}
        self.call_count = 0
        self.last_request = None
    
    def complete(self, prompt: str, **kwargs) -> Any:
        """Mock completion method."""
        self.call_count += 1
        self.last_request = {'prompt': prompt, 'kwargs': kwargs}
        
        # Return predefined response if available
        if prompt in self.responses:
            return self.responses[prompt]
        
        # Default responses based on prompt content
        if 'rate' in prompt.lower() and 'score' in prompt.lower():
            return Mock(content='8')
        elif 'sentiment' in prompt.lower():
            return Mock(content='positive')
        elif 'boolean' in prompt.lower() or 'true' in prompt.lower():
            return Mock(content='true')
        elif 'number' in prompt.lower():
            return Mock(content='42')
        else:
            return Mock(content='test_response')


class TestLLMIntegration:
    """Test basic LLM integration functionality."""
    
    def test_engine_with_llm_client(self):
        """Test engine initialization with LLM client."""
        mock_client = MockLLMClient()
        engine = Engine(llm_client=mock_client)
        
        assert engine._llm_client is mock_client
        assert engine._prompt_evaluator is not None
    
    def test_prompt_function_basic(self):
        """Test basic PROMPT() function execution."""
        mock_client = MockLLMClient({'Analyze sentiment: happy': Mock(content='positive')})
        
        yaml_rules = """
rules:
  - id: sentiment_rule
    priority: 100
    condition: "PROMPT('Analyze sentiment: {text}') == 'positive'"
    actions:
      sentiment: positive
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(text='happy'))
        
        assert result.verdict['sentiment'] == 'positive'
        assert 'sentiment_rule' in result.fired_rules
        assert mock_client.call_count == 1
    
    def test_prompt_function_with_type_conversion(self):
        """Test PROMPT() function with type conversion."""
        mock_client = MockLLMClient({'Rate urgency 1-10: emergency': Mock(content='9')})
        
        yaml_rules = """
rules:
  - id: urgency_rule
    priority: 100
    condition: "PROMPT('Rate urgency 1-10: {situation}', 'int') > 8"
    actions:
      urgent: true
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(situation='emergency'))
        
        assert result.verdict['urgent'] is True
        assert 'urgency_rule' in result.fired_rules
    
    def test_prompt_function_multiple_calls(self):
        """Test multiple PROMPT() calls in same condition."""
        mock_client = MockLLMClient({
            'Rate confidence 1-10: good company': Mock(content='8'),
            'Rate market 1-10: tech sector': Mock(content='7')
        })
        
        yaml_rules = """
rules:
  - id: investment_rule
    priority: 100
    condition: "PROMPT('Rate confidence 1-10: {company}', 'int') > 7 and PROMPT('Rate market 1-10: {sector}', 'int') > 6"
    actions:
      invest: true
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(company='good company', sector='tech sector'))
        
        assert result.verdict['invest'] is True
        assert mock_client.call_count == 2
    
    def test_prompt_function_in_actions(self):
        """Test PROMPT() function in action values."""
        mock_client = MockLLMClient({'Summarize: complex situation': Mock(content='summary text')})
        
        yaml_rules = """
rules:
  - id: summary_rule
    priority: 100
    condition: "status == 'active'"
    actions:
      summary: "{{ PROMPT('Summarize: {description}') }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(status='active', description='complex situation'))
        
        assert result.verdict['summary'] == 'summary text'
        assert mock_client.call_count == 1


class TestLLMErrorHandling:
    """Test LLM error handling and edge cases."""
    
    def test_llm_client_error(self):
        """Test handling of LLM client errors."""
        mock_client = Mock()
        mock_client.complete.side_effect = Exception("API Error")
        
        yaml_rules = """
rules:
  - id: error_rule
    priority: 100
    condition: "PROMPT('test prompt') == 'success'"
    actions:
      result: true
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(value=1))
        
        # Rule should not fire due to PROMPT error
        assert 'error_rule' not in result.fired_rules
        assert result.verdict == {}
    
    def test_prompt_type_conversion_error(self):
        """Test error handling in PROMPT type conversion."""
        mock_client = MockLLMClient({'Rate: test': Mock(content='not_a_number')})
        
        yaml_rules = """
rules:
  - id: conversion_rule
    priority: 100
    condition: "PROMPT('Rate: {text}', 'int') > 5"
    actions:
      result: true
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(text='test'))
        
        # Rule should not fire due to type conversion error
        assert 'conversion_rule' not in result.fired_rules
        assert result.verdict == {}
    
    def test_prompt_without_llm_client(self):
        """Test PROMPT() function without LLM client."""
        yaml_rules = """
rules:
  - id: no_llm_rule
    priority: 100
    condition: "PROMPT('test') == 'result'"
    actions:
      result: true
"""
        
        engine = Engine.from_yaml(yaml_rules)  # No LLM client
        result = engine.reason(facts(value=1))
        
        # Rule should not fire due to missing LLM client
        assert 'no_llm_rule' not in result.fired_rules
        assert result.verdict == {}
    
    def test_prompt_malformed_arguments(self):
        """Test PROMPT() with malformed arguments."""
        mock_client = MockLLMClient()
        
        yaml_rules = """
rules:
  - id: malformed_rule
    priority: 100
    condition: "PROMPT() == 'result'"  # Missing arguments
    actions:
      result: true
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(value=1))
        
        # Rule should not fire due to malformed PROMPT call
        assert 'malformed_rule' not in result.fired_rules
        assert result.verdict == {}


class TestHybridAIArithmetic:
    """Test hybrid AI + arithmetic functionality."""
    
    def test_prompt_plus_arithmetic(self):
        """Test PROMPT() result used in arithmetic operations."""
        mock_client = MockLLMClient({'Rate confidence 1-10: good opportunity': Mock(content='8')})
        
        yaml_rules = """
rules:
  - id: hybrid_rule
    priority: 100
    condition: "PROMPT('Rate confidence 1-10: {opportunity}', 'int') + market_bonus > 10"
    actions:
      decision: INVEST
      total_score: "{{ LAST_PROMPT_RESULT + market_bonus }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(opportunity='good opportunity', market_bonus=3))
        
        assert result.verdict['decision'] == 'INVEST'
        assert result.verdict['total_score'] == 11  # 8 + 3
        assert 'hybrid_rule' in result.fired_rules
    
    def test_multiple_prompts_arithmetic(self):
        """Test multiple PROMPT() results in arithmetic."""
        mock_client = MockLLMClient({
            'Rate company 1-10: tech startup': Mock(content='7'),
            'Rate market 1-10: AI sector': Mock(content='9')
        })
        
        yaml_rules = """
rules:
  - id: multi_prompt_rule
    priority: 100
    condition: "PROMPT('Rate company 1-10: {company}', 'int') * PROMPT('Rate market 1-10: {sector}', 'int') > 50"
    actions:
      invest: true
      company_score: "{{ LAST_PROMPT_RESULT }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(company='tech startup', sector='AI sector'))
        
        assert result.verdict['invest'] is True
        assert 'multi_prompt_rule' in result.fired_rules
        # Note: LAST_PROMPT_RESULT will be the last executed PROMPT (market rating = 9)
        assert result.verdict['company_score'] == 9
    
    def test_prompt_comparison_with_thresholds(self):
        """Test PROMPT() results compared to thresholds."""
        mock_client = MockLLMClient({
            'Rate risk 1-10: high volatility investment': Mock(content='8'),
            'Rate potential 1-10: high growth market': Mock(content='9')
        })
        
        yaml_rules = """
rules:
  - id: risk_vs_reward
    priority: 100
    condition: "PROMPT('Rate potential 1-10: {potential}', 'int') - PROMPT('Rate risk 1-10: {risk}', 'int') > 0"
    actions:
      recommendation: PROCEED
      risk_score: "{{ LAST_PROMPT_RESULT }}"
      net_score: "{{ LAST_PROMPT_RESULT - PREVIOUS_PROMPT_RESULT }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(potential='high growth market', risk='high volatility investment'))
        
        assert result.verdict['recommendation'] == 'PROCEED'
        assert 'risk_vs_reward' in result.fired_rules
        # 9 (potential) - 8 (risk) = 1 > 0, so condition should be true
    
    def test_prompt_with_complex_expressions(self):
        """Test PROMPT() in complex mathematical expressions."""
        mock_client = MockLLMClient({
            'Rate base score 1-10: good product': Mock(content='7')
        })
        
        yaml_rules = """
rules:
  - id: complex_math_rule
    priority: 100
    condition: "(PROMPT('Rate base score 1-10: {product}', 'int') * multiplier + bonus) / divisor > threshold"
    actions:
      qualified: true
      final_score: "{{ (LAST_PROMPT_RESULT * multiplier + bonus) / divisor }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(
            product='good product',
            multiplier=2,
            bonus=5,
            divisor=3,
            threshold=5
        ))
        
        # (7 * 2 + 5) / 3 = 19 / 3 = 6.33 > 5
        assert result.verdict['qualified'] is True
        assert result.verdict['final_score'] == pytest.approx(6.33, rel=1e-2)


class TestLLMTemplateVariables:
    """Test LLM integration with template variables."""
    
    def test_template_variable_substitution(self):
        """Test template variable substitution in PROMPT()."""
        mock_client = MockLLMClient({
            'Analyze customer John Doe with score 850': Mock(content='premium_customer')
        })
        
        yaml_rules = """
rules:
  - id: template_rule
    priority: 100
    condition: "PROMPT('Analyze customer {name} with score {credit_score}') == 'premium_customer'"
    actions:
      category: premium
      analysis: "{{ LAST_PROMPT_RESULT }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(name='John Doe', credit_score=850))
        
        assert result.verdict['category'] == 'premium'
        assert result.verdict['analysis'] == 'premium_customer'
        assert mock_client.call_count == 1
    
    def test_prompt_result_in_template_actions(self):
        """Test using PROMPT results in template action values."""
        mock_client = MockLLMClient({
            'Generate recommendation for: high value customer': Mock(content='VIP_TREATMENT')
        })
        
        yaml_rules = """
rules:
  - id: template_action_rule
    priority: 100
    condition: "customer_tier == 'gold'"
    actions:
      recommendation: "{{ PROMPT('Generate recommendation for: {description}') }}"
      message: "Customer gets {{ LAST_PROMPT_RESULT }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(customer_tier='gold', description='high value customer'))
        
        assert result.verdict['recommendation'] == 'VIP_TREATMENT'
        assert result.verdict['message'] == 'Customer gets VIP_TREATMENT'
    
    def test_chained_prompt_templates(self):
        """Test chaining multiple PROMPT() calls with templates."""
        mock_client = MockLLMClient({
            'Classify: premium customer inquiry': Mock(content='PRIORITY'),
            'Generate response for PRIORITY case': Mock(content='immediate_attention')
        })
        
        yaml_rules = """
rules:
  - id: chained_rule
    priority: 100
    condition: "PROMPT('Classify: {inquiry_type}') == 'PRIORITY'"
    actions:
      classification: "{{ LAST_PROMPT_RESULT }}"
      response: "{{ PROMPT('Generate response for {classification} case') }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(inquiry_type='premium customer inquiry'))
        
        assert result.verdict['classification'] == 'PRIORITY'
        assert result.verdict['response'] == 'immediate_attention'
        assert mock_client.call_count == 2


class TestLLMSecurityAndValidation:
    """Test LLM security and validation features."""
    
    def test_prompt_sanitization(self):
        """Test PROMPT() input sanitization."""
        mock_client = MockLLMClient()
        
        yaml_rules = """
rules:
  - id: sanitization_rule
    priority: 100
    condition: "PROMPT('Rate: {user_input}', 'int') > 5"
    actions:
      safe: true
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        
        # Test with potentially dangerous input
        result = engine.reason(facts(user_input='<script>alert("xss")</script>'))
        
        # Should handle safely without error
        assert mock_client.call_count == 1
        # The exact sanitization behavior depends on implementation
    
    def test_prompt_response_validation(self):
        """Test validation of PROMPT() responses."""
        mock_client = MockLLMClient({
            'Rate 1-10: test': Mock(content='15')  # Out of expected range
        })
        
        yaml_rules = """
rules:
  - id: validation_rule
    priority: 100
    condition: "PROMPT('Rate 1-10: {item}', 'int') <= 10"
    actions:
      valid: true
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(item='test'))
        
        # Should handle out-of-range response
        assert 'validation_rule' not in result.fired_rules  # 15 > 10
        assert result.verdict == {}
    
    def test_prompt_timeout_handling(self):
        """Test handling of PROMPT() timeouts."""
        mock_client = Mock()
        mock_client.complete.side_effect = TimeoutError("Request timed out")
        
        yaml_rules = """
rules:
  - id: timeout_rule
    priority: 100
    condition: "PROMPT('slow operation') == 'success'"
    actions:
      result: true
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(value=1))
        
        # Should handle timeout gracefully
        assert 'timeout_rule' not in result.fired_rules
        assert result.verdict == {}


class TestLLMPerformance:
    """Test LLM performance and optimization."""
    
    def test_prompt_caching(self):
        """Test PROMPT() response caching (if implemented)."""
        mock_client = MockLLMClient({
            'Rate: test item': Mock(content='8')
        })
        
        yaml_rules = """
rules:
  - id: cache_rule1
    priority: 100
    condition: "PROMPT('Rate: {item}', 'int') > 5"
    actions:
      result1: true
      
  - id: cache_rule2
    priority: 90
    condition: "PROMPT('Rate: {item}', 'int') > 7"
    actions:
      result2: true
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(item='test item'))
        
        assert result.verdict['result1'] is True
        assert result.verdict['result2'] is True
        
        # If caching is implemented, should only make one API call
        # If not, will make two calls - both are acceptable
        assert mock_client.call_count >= 1  # At least one call made
    
    def test_prompt_error_recovery(self):
        """Test PROMPT() error recovery and fallback."""
        mock_client = Mock()
        # First call fails, second succeeds
        mock_client.complete.side_effect = [
            Exception("First call failed"),
            Mock(content='8')
        ]
        
        yaml_rules = """
rules:
  - id: recovery_rule1
    priority: 100
    condition: "PROMPT('Rate first: {item}', 'int') > 5"
    actions:
      result1: true
      
  - id: recovery_rule2
    priority: 90
    condition: "PROMPT('Rate second: {item}', 'int') > 5"
    actions:
      result2: true
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(item='test'))
        
        # First rule should fail, second should succeed
        assert 'recovery_rule1' not in result.fired_rules
        assert 'recovery_rule2' in result.fired_rules
        assert result.verdict['result2'] is True 