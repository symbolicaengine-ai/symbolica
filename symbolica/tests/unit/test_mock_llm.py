"""
Unit Tests for Mock LLM Integration
==================================

Tests that can run without API keys using mock LLM responses.
These tests ensure the LLM integration works correctly even when
no actual LLM client is available.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from symbolica import Engine, facts


class MockLLMClient:
    """Complete mock LLM client that mimics real LLM behavior."""
    
    def __init__(self, responses=None, default_response="5"):
        self.responses = responses or {}
        self.default_response = default_response
        self.call_count = 0
        self.call_history = []
        self.last_prompt = None
        self.last_kwargs = None
    
    def complete(self, prompt, **kwargs):
        """Mock the complete method."""
        self.call_count += 1
        self.last_prompt = prompt
        self.last_kwargs = kwargs
        self.call_history.append((prompt, kwargs))
        
        # Return specific response if available
        if prompt in self.responses:
            response = self.responses[prompt]
        else:
            response = self.default_response
        
        # Return mock response object
        return Mock(content=response, usage=Mock(total_tokens=10))
    
    def reset(self):
        """Reset mock state."""
        self.call_count = 0
        self.call_history = []
        self.last_prompt = None
        self.last_kwargs = None


class TestMockLLMBasics:
    """Test basic LLM functionality with mocks."""
    
    def test_mock_llm_client_setup(self):
        """Test that mock LLM client is set up correctly."""
        mock_client = MockLLMClient()
        engine = Engine(llm_client=mock_client)
        
        # Check that LLM client is properly integrated
        assert engine._llm_client is mock_client
        assert engine._prompt_evaluator is not None
    
    def test_prompt_function_with_mock(self):
        """Test PROMPT() function with mock responses."""
        mock_client = MockLLMClient(responses={
            'Rate confidence 1-10: good investment': '8'
        })
        
        yaml_rules = """
rules:
  - id: mock_prompt_test
    priority: 100
    condition: "PROMPT('Rate confidence 1-10: {investment}') == '8'"
    actions:
      confidence_level: high
      ai_response: "{{ LAST_PROMPT_RESULT }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(investment='good investment'))
        
        # Check results
        assert result.verdict['confidence_level'] == 'high'
        assert result.verdict['ai_response'] == '8'
        assert 'mock_prompt_test' in result.fired_rules
        assert mock_client.call_count == 1
    
    def test_prompt_type_conversion_with_mock(self):
        """Test PROMPT() type conversion with mock responses."""
        mock_client = MockLLMClient(responses={
            'Rate 1-10: test item': '7'
        })
        
        yaml_rules = """
rules:
  - id: type_conversion_test
    priority: 100
    condition: "PROMPT('Rate 1-10: {item}', 'int') > 5"
    actions:
      approved: true
      numeric_score: "{{ LAST_PROMPT_RESULT }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(item='test item'))
        
        # Check type conversion worked
        assert result.verdict['approved'] is True
        assert result.verdict['numeric_score'] == 7  # Should be converted to int
        assert mock_client.call_count == 1
    
    def test_multiple_prompt_calls_with_mock(self):
        """Test multiple PROMPT() calls with mock responses."""
        mock_client = MockLLMClient(responses={
            'Rate company 1-10: tech startup': '6',
            'Rate market 1-10: AI industry': '8'
        })
        
        yaml_rules = """
rules:
  - id: multiple_prompts_test
    priority: 100
    condition: "PROMPT('Rate company 1-10: {company}', 'int') + PROMPT('Rate market 1-10: {market}', 'int') > 12"
    actions:
      investment_decision: BUY
      company_score: "{{ LAST_PROMPT_RESULT }}"
      combined_score: "{{ LAST_PROMPT_RESULT + PREVIOUS_PROMPT_RESULT }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(company='tech startup', market='AI industry'))
        
        # Check multiple prompts worked (6 + 8 = 14 > 12)
        assert result.verdict['investment_decision'] == 'BUY'
        assert result.verdict['company_score'] == 8  # Last prompt result
        assert mock_client.call_count == 2
    
    def test_prompt_in_action_templates_with_mock(self):
        """Test PROMPT() in action template values with mock responses."""
        mock_client = MockLLMClient(responses={
            'Generate summary for: complex business scenario': 'Strategic analysis complete'
        })
        
        yaml_rules = """
rules:
  - id: prompt_in_actions_test
    priority: 100
    condition: "status == 'ready'"
    actions:
      analysis_summary: "{{ PROMPT('Generate summary for: {scenario}') }}"
      processing_complete: true
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(status='ready', scenario='complex business scenario'))
        
        # Check prompt in action worked
        assert result.verdict['analysis_summary'] == 'Strategic analysis complete'
        assert result.verdict['processing_complete'] is True
        assert mock_client.call_count == 1


class TestMockLLMErrorHandling:
    """Test error handling with mock LLM responses."""
    
    def test_mock_llm_error_simulation(self):
        """Test simulating LLM errors with mock."""
        mock_client = Mock()
        mock_client.complete.side_effect = Exception("Simulated API error")
        
        yaml_rules = """
rules:
  - id: error_simulation_test
    priority: 100
    condition: "PROMPT('test prompt') == 'success'"
    actions:
      should_not_trigger: true
      
  - id: fallback_rule
    priority: 90
    condition: "backup_score > 5"
    actions:
      fallback_triggered: true
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(backup_score=7))
        
        # First rule should fail, second should succeed
        assert 'error_simulation_test' not in result.fired_rules
        assert 'fallback_rule' in result.fired_rules
        assert result.verdict['fallback_triggered'] is True
    
    def test_mock_invalid_response_handling(self):
        """Test handling invalid mock responses."""
        mock_client = MockLLMClient(responses={
            'Rate 1-10: invalid response test': 'not_a_number'
        })
        
        yaml_rules = """
rules:
  - id: invalid_response_test
    priority: 100
    condition: "PROMPT('Rate 1-10: {item}', 'int') > 5"
    actions:
      should_not_trigger: true
      
  - id: fallback_rule
    priority: 90
    condition: "True"
    actions:
      fallback_used: true
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(item='invalid response test'))
        
        # First rule should fail due to type conversion error
        assert 'invalid_response_test' not in result.fired_rules
        assert 'fallback_rule' in result.fired_rules
        assert result.verdict['fallback_used'] is True
    
    def test_mock_timeout_simulation(self):
        """Test simulating timeout with mock."""
        mock_client = Mock()
        mock_client.complete.side_effect = TimeoutError("Simulated timeout")
        
        yaml_rules = """
rules:
  - id: timeout_test
    priority: 100
    condition: "PROMPT('slow operation') == 'done'"
    actions:
      should_not_trigger: true
      
  - id: timeout_fallback
    priority: 90
    condition: "timeout_occurred == True"
    actions:
      timeout_handled: true
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(timeout_occurred=True))
        
        # First rule should fail, fallback should work
        assert 'timeout_test' not in result.fired_rules
        assert 'timeout_fallback' in result.fired_rules
        assert result.verdict['timeout_handled'] is True


class TestMockLLMBusinessScenarios:
    """Test realistic business scenarios with mock LLM."""
    
    def test_mock_customer_sentiment_analysis(self):
        """Test customer sentiment analysis with mock responses."""
        mock_client = MockLLMClient(responses={
            'Analyze sentiment of: Your service is excellent!': 'positive',
            'Analyze sentiment of: This is terrible service': 'negative',
            'Analyze sentiment of: It was okay': 'neutral'
        })
        
        yaml_rules = """
rules:
  - id: positive_sentiment
    priority: 100
    condition: "PROMPT('Analyze sentiment of: {feedback}') == 'positive'"
    actions:
      sentiment: positive
      action: thank_customer
      priority: high
      
  - id: negative_sentiment
    priority: 90
    condition: "PROMPT('Analyze sentiment of: {feedback}') == 'negative'"
    actions:
      sentiment: negative
      action: escalate_to_manager
      priority: urgent
      
  - id: neutral_sentiment
    priority: 80
    condition: "PROMPT('Analyze sentiment of: {feedback}') == 'neutral'"
    actions:
      sentiment: neutral
      action: standard_response
      priority: normal
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        
        # Test positive sentiment
        result1 = engine.reason(facts(feedback='Your service is excellent!'))
        assert result1.verdict['sentiment'] == 'positive'
        assert result1.verdict['action'] == 'thank_customer'
        assert result1.verdict['priority'] == 'high'
        
        # Test negative sentiment
        result2 = engine.reason(facts(feedback='This is terrible service'))
        assert result2.verdict['sentiment'] == 'negative'
        assert result2.verdict['action'] == 'escalate_to_manager'
        assert result2.verdict['priority'] == 'urgent'
        
        # Test neutral sentiment
        result3 = engine.reason(facts(feedback='It was okay'))
        assert result3.verdict['sentiment'] == 'neutral'
        assert result3.verdict['action'] == 'standard_response'
        assert result3.verdict['priority'] == 'normal'
    
    def test_mock_risk_assessment_scenario(self):
        """Test risk assessment scenario with mock responses."""
        mock_client = MockLLMClient(responses={
            'Assess risk 1-10 for: Large international transfer': '8',
            'Assess risk 1-10 for: Small local purchase': '2',
            'Assess risk 1-10 for: Regular monthly payment': '1'
        })
        
        yaml_rules = """
rules:
  - id: high_risk_transaction
    priority: 100
    condition: "PROMPT('Assess risk 1-10 for: {transaction}', 'int') >= 7"
    actions:
      risk_level: HIGH
      requires_approval: true
      ai_risk_score: "{{ LAST_PROMPT_RESULT }}"
      
  - id: medium_risk_transaction
    priority: 90
    condition: "PROMPT('Assess risk 1-10 for: {transaction}', 'int') >= 4 and PROMPT('Assess risk 1-10 for: {transaction}', 'int') < 7"
    actions:
      risk_level: MEDIUM
      requires_approval: false
      ai_risk_score: "{{ LAST_PROMPT_RESULT }}"
      
  - id: low_risk_transaction
    priority: 80
    condition: "PROMPT('Assess risk 1-10 for: {transaction}', 'int') < 4"
    actions:
      risk_level: LOW
      requires_approval: false
      ai_risk_score: "{{ LAST_PROMPT_RESULT }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        
        # Test high risk
        result1 = engine.reason(facts(transaction='Large international transfer'))
        assert result1.verdict['risk_level'] == 'HIGH'
        assert result1.verdict['requires_approval'] is True
        assert result1.verdict['ai_risk_score'] == 8
        
        # Test low risk
        result2 = engine.reason(facts(transaction='Regular monthly payment'))
        assert result2.verdict['risk_level'] == 'LOW'
        assert result2.verdict['requires_approval'] is False
        assert result2.verdict['ai_risk_score'] == 1
    
    def test_mock_content_moderation_scenario(self):
        """Test content moderation with mock responses."""
        mock_client = MockLLMClient(responses={
            'Rate content safety 1-10: This is inappropriate content': '2',
            'Rate content safety 1-10: This is helpful information': '9',
            'Rate content safety 1-10: This is borderline content': '5'
        })
        
        yaml_rules = """
rules:
  - id: content_blocked
    priority: 100
    condition: "PROMPT('Rate content safety 1-10: {content}', 'int') <= 3"
    actions:
      moderation_action: BLOCK
      reason: INAPPROPRIATE_CONTENT
      ai_safety_score: "{{ LAST_PROMPT_RESULT }}"
      
  - id: content_approved
    priority: 90
    condition: "PROMPT('Rate content safety 1-10: {content}', 'int') >= 8"
    actions:
      moderation_action: APPROVE
      reason: SAFE_CONTENT
      ai_safety_score: "{{ LAST_PROMPT_RESULT }}"
      
  - id: content_review
    priority: 80
    condition: "PROMPT('Rate content safety 1-10: {content}', 'int') > 3 and PROMPT('Rate content safety 1-10: {content}', 'int') < 8"
    actions:
      moderation_action: REVIEW
      reason: NEEDS_HUMAN_REVIEW
      ai_safety_score: "{{ LAST_PROMPT_RESULT }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        
        # Test blocked content
        result1 = engine.reason(facts(content='This is inappropriate content'))
        assert result1.verdict['moderation_action'] == 'BLOCK'
        assert result1.verdict['reason'] == 'INAPPROPRIATE_CONTENT'
        assert result1.verdict['ai_safety_score'] == 2
        
        # Test approved content
        result2 = engine.reason(facts(content='This is helpful information'))
        assert result2.verdict['moderation_action'] == 'APPROVE'
        assert result2.verdict['reason'] == 'SAFE_CONTENT'
        assert result2.verdict['ai_safety_score'] == 9
        
        # Test review content
        result3 = engine.reason(facts(content='This is borderline content'))
        assert result3.verdict['moderation_action'] == 'REVIEW'
        assert result3.verdict['reason'] == 'NEEDS_HUMAN_REVIEW'
        assert result3.verdict['ai_safety_score'] == 5


class TestMockLLMPerformance:
    """Test performance characteristics with mock LLM."""
    
    def test_mock_llm_call_counting(self):
        """Test that mock LLM correctly counts calls."""
        mock_client = MockLLMClient(default_response='6')
        
        yaml_rules = """
rules:
  - id: call_counting_test
    priority: 100
    condition: "PROMPT('Rate: {item1}', 'int') + PROMPT('Rate: {item2}', 'int') > 10"
    actions:
      total_calls: "{{ LAST_PROMPT_RESULT }}"
      result: success
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(item1='test1', item2='test2'))
        
        # Should have made 2 calls (6 + 6 = 12 > 10)
        assert mock_client.call_count == 2
        assert result.verdict['result'] == 'success'
        assert len(mock_client.call_history) == 2
    
    def test_mock_llm_call_history(self):
        """Test that mock LLM maintains call history."""
        mock_client = MockLLMClient(responses={
            'First call': 'response1',
            'Second call': 'response2'
        })
        
        yaml_rules = """
rules:
  - id: history_test1
    priority: 100
    condition: "PROMPT('First call') == 'response1'"
    actions:
      first_result: "{{ LAST_PROMPT_RESULT }}"
      
  - id: history_test2
    priority: 90
    condition: "PROMPT('Second call') == 'response2'"
    actions:
      second_result: "{{ LAST_PROMPT_RESULT }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts())
        
        # Check call history
        assert mock_client.call_count == 2
        assert len(mock_client.call_history) == 2
        assert mock_client.call_history[0][0] == 'First call'
        assert mock_client.call_history[1][0] == 'Second call'
        
        # Check results
        assert result.verdict['first_result'] == 'response1'
        assert result.verdict['second_result'] == 'response2'
    
    def test_mock_llm_reset_functionality(self):
        """Test that mock LLM can be reset."""
        mock_client = MockLLMClient(default_response='7')
        
        yaml_rules = """
rules:
  - id: reset_test
    priority: 100
    condition: "PROMPT('Test prompt') == '7'"
    actions:
      test_result: success
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        
        # First execution
        result1 = engine.reason(facts())
        assert mock_client.call_count == 1
        assert result1.verdict['test_result'] == 'success'
        
        # Reset mock
        mock_client.reset()
        assert mock_client.call_count == 0
        assert len(mock_client.call_history) == 0
        
        # Second execution
        result2 = engine.reason(facts())
        assert mock_client.call_count == 1
        assert result2.verdict['test_result'] == 'success'


class TestMockLLMConfigurationTesting:
    """Test different LLM configurations with mock."""
    
    def test_mock_llm_with_different_response_patterns(self):
        """Test mock LLM with different response patterns."""
        # Test with numeric responses
        numeric_mock = MockLLMClient(default_response='8')
        
        yaml_rules = """
rules:
  - id: numeric_test
    priority: 100
    condition: "PROMPT('Rate numerically: {item}', 'int') > 5"
    actions:
      numeric_result: "{{ LAST_PROMPT_RESULT }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=numeric_mock)
        result = engine.reason(facts(item='test'))
        
        assert result.verdict['numeric_result'] == 8
        
        # Test with boolean responses
        boolean_mock = MockLLMClient(default_response='true')
        
        yaml_rules_bool = """
rules:
  - id: boolean_test
    priority: 100
    condition: "PROMPT('Is this valid: {item}', 'bool') == True"
    actions:
      boolean_result: "{{ LAST_PROMPT_RESULT }}"
"""
        
        engine_bool = Engine.from_yaml(yaml_rules_bool, llm_client=boolean_mock)
        result_bool = engine_bool.reason(facts(item='test'))
        
        assert result_bool.verdict['boolean_result'] is True
    
    def test_mock_llm_without_client(self):
        """Test behavior when no LLM client is provided."""
        yaml_rules = """
rules:
  - id: no_client_test
    priority: 100
    condition: "PROMPT('Test without client') == 'should_not_work'"
    actions:
      should_not_trigger: true
      
  - id: fallback_without_llm
    priority: 90
    condition: "manual_condition == True"
    actions:
      fallback_works: true
"""
        
        # Engine without LLM client
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(manual_condition=True))
        
        # LLM rule should not fire, fallback should work
        assert 'no_client_test' not in result.fired_rules
        assert 'fallback_without_llm' in result.fired_rules
        assert result.verdict['fallback_works'] is True
    
    def test_mock_llm_with_custom_configuration(self):
        """Test mock LLM with custom configuration."""
        mock_client = MockLLMClient(responses={
            'Custom prompt format: analyze data': 'custom_response'
        })
        
        yaml_rules = """
rules:
  - id: custom_config_test
    priority: 100
    condition: "PROMPT('Custom prompt format: {action}') == 'custom_response'"
    actions:
      custom_result: "{{ LAST_PROMPT_RESULT }}"
      configuration: custom
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(action='analyze data'))
        
        assert result.verdict['custom_result'] == 'custom_response'
        assert result.verdict['configuration'] == 'custom'
        assert mock_client.call_count == 1 