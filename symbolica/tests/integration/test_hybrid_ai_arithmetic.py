"""
Integration Tests for Hybrid AI + Arithmetic
===========================================

Tests for the revolutionary hybrid AI + arithmetic functionality that combines
OpenAI intelligence with symbolic precision and logical reasoning.
"""

import pytest
from unittest.mock import Mock, MagicMock
from symbolica import Engine, facts


class MockLLMResponse:
    """Mock LLM response for testing."""
    def __init__(self, content: str, cost: float = 0.001, latency_ms: float = 500):
        self.content = content
        self.cost = cost
        self.latency_ms = latency_ms


class MockLLMClient:
    """Mock LLM client for consistent testing."""
    
    def __init__(self, response_map=None):
        self.response_map = response_map or {}
        self.call_count = 0
        self.call_history = []
    
    def complete(self, prompt, **kwargs):
        self.call_count += 1
        self.call_history.append(prompt)
        
        # Return specific response if mapped
        if prompt in self.response_map:
            return self.response_map[prompt]
        
        # Default intelligent responses based on prompt content
        if 'confidence' in prompt.lower() and 'investment' in prompt.lower():
            if 'established' in prompt.lower() or 'profitable' in prompt.lower():
                return MockLLMResponse('9')
            elif 'startup' in prompt.lower() or 'unproven' in prompt.lower():
                return MockLLMResponse('3')
            else:
                return MockLLMResponse('6')
        
        elif 'risk' in prompt.lower():
            if 'high' in prompt.lower():
                return MockLLMResponse('8')
            elif 'low' in prompt.lower():
                return MockLLMResponse('2')
            else:
                return MockLLMResponse('5')
        
        elif 'sentiment' in prompt.lower():
            if 'happy' in prompt.lower() or 'great' in prompt.lower():
                return MockLLMResponse('positive')
            elif 'sad' in prompt.lower() or 'bad' in prompt.lower():
                return MockLLMResponse('negative')
            else:
                return MockLLMResponse('neutral')
        
        elif 'urgency' in prompt.lower():
            if 'emergency' in prompt.lower() or 'urgent' in prompt.lower():
                return MockLLMResponse('9')
            else:
                return MockLLMResponse('3')
        
        # Default numeric response
        return MockLLMResponse('5')


class TestHybridAIArithmetic:
    """Test hybrid AI + arithmetic functionality."""
    
    def test_basic_ai_plus_arithmetic(self):
        """Test basic AI analysis plus arithmetic operations."""
        mock_client = MockLLMClient({
            'Rate investment confidence 1-10 for: tech startup': MockLLMResponse('7')
        })
        
        yaml_rules = """
rules:
  - id: investment_decision
    priority: 100
    condition: "PROMPT('Rate investment confidence 1-10 for: {description}', 'int') + market_bonus > 10"
    actions:
      should_invest: true
      decision: INVEST
      ai_score: "{{ LAST_PROMPT_RESULT }}"
      total_score: "{{ LAST_PROMPT_RESULT + market_bonus }}"
      reason: MEETS_THRESHOLD
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(description='tech startup', market_bonus=4))
        
        # AI score (7) + market bonus (4) = 11 > 10, so should trigger
        assert result.verdict['should_invest'] is True
        assert result.verdict['decision'] == 'INVEST'
        assert result.verdict['ai_score'] == 7
        assert result.verdict['total_score'] == 11
        assert result.verdict['reason'] == 'MEETS_THRESHOLD'
        assert 'investment_decision' in result.fired_rules
    
    def test_ai_threshold_comparison(self):
        """Test AI-generated values compared to thresholds."""
        mock_client = MockLLMClient({
            'Rate business risk 1-10 for: small startup': MockLLMResponse('8'),
            'Rate business risk 1-10 for: large corporation': MockLLMResponse('3')
        })
        
        yaml_rules = """
rules:
  - id: high_risk_alert
    priority: 100
    condition: "PROMPT('Rate business risk 1-10 for: {business_type}', 'int') > 6"
    actions:
      risk_level: HIGH
      requires_review: true
      ai_risk_score: "{{ LAST_PROMPT_RESULT }}"
      
  - id: low_risk_approval
    priority: 90
    condition: "PROMPT('Rate business risk 1-10 for: {business_type}', 'int') <= 4"
    actions:
      risk_level: LOW
      auto_approve: true
      ai_risk_score: "{{ LAST_PROMPT_RESULT }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        
        # High risk case
        result1 = engine.reason(facts(business_type='small startup'))
        assert result1.verdict['risk_level'] == 'HIGH'
        assert result1.verdict['requires_review'] is True
        assert result1.verdict['ai_risk_score'] == 8
        assert 'high_risk_alert' in result1.fired_rules
        
        # Low risk case  
        result2 = engine.reason(facts(business_type='large corporation'))
        assert result2.verdict['risk_level'] == 'LOW'
        assert result2.verdict['auto_approve'] is True
        assert result2.verdict['ai_risk_score'] == 3
        assert 'low_risk_approval' in result2.fired_rules
    
    def test_multiple_ai_values_arithmetic(self):
        """Test arithmetic operations with multiple AI-generated values."""
        mock_client = MockLLMClient({
            'Rate company strength 1-10: established tech company': MockLLMResponse('8'),
            'Rate market conditions 1-10: AI sector': MockLLMResponse('9')
        })
        
        yaml_rules = """
rules:
  - id: compound_analysis
    priority: 100
    condition: "PROMPT('Rate company strength 1-10: {company}', 'int') * PROMPT('Rate market conditions 1-10: {market}', 'int') > 60"
    actions:
      decision: STRONG_BUY
      company_score: "{{ LAST_PROMPT_RESULT }}"
      combined_score: "{{ LAST_PROMPT_RESULT * PREVIOUS_PROMPT_RESULT }}"
      multiplier_bonus: "{{ combined_score * 0.1 }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(company='established tech company', market='AI sector'))
        
        # Company (8) * Market (9) = 72 > 60, so should trigger
        assert result.verdict['decision'] == 'STRONG_BUY'
        assert result.verdict['company_score'] == 9  # Last PROMPT result (market)
        # Note: The exact combined score depends on PROMPT execution order
        assert 'compound_analysis' in result.fired_rules
    
    def test_ai_arithmetic_with_business_logic(self):
        """Test AI + arithmetic + business logic combination."""
        mock_client = MockLLMClient({
            'Analyze credit worthiness 1-10: good payment history, stable income': MockLLMResponse('8')
        })
        
        yaml_rules = """
rules:
  - id: credit_approval
    priority: 100
    condition: "PROMPT('Analyze credit worthiness 1-10: {credit_profile}', 'int') + income_bonus >= approval_threshold"
    actions:
      approved: true
      credit_limit: "{{ (LAST_PROMPT_RESULT + income_bonus) * 1000 }}"
      ai_credit_score: "{{ LAST_PROMPT_RESULT }}"
      total_score: "{{ LAST_PROMPT_RESULT + income_bonus }}"
      decision: APPROVED
      
  - id: credit_denial
    priority: 90
    condition: "PROMPT('Analyze credit worthiness 1-10: {credit_profile}', 'int') + income_bonus < approval_threshold"
    actions:
      approved: false
      credit_limit: 0
      ai_credit_score: "{{ LAST_PROMPT_RESULT }}"
      total_score: "{{ LAST_PROMPT_RESULT + income_bonus }}"
      decision: DENIED
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(
            credit_profile='good payment history, stable income',
            income_bonus=3,
            approval_threshold=10
        ))
        
        # AI score (8) + income bonus (3) = 11 >= 10, so should approve
        assert result.verdict['approved'] is True
        assert result.verdict['credit_limit'] == 11000  # (8 + 3) * 1000
        assert result.verdict['ai_credit_score'] == 8
        assert result.verdict['total_score'] == 11
        assert result.verdict['decision'] == 'APPROVED'
        assert 'credit_approval' in result.fired_rules
    
    def test_ai_generated_weights_in_formulas(self):
        """Test using AI-generated values as weights in complex formulas."""
        mock_client = MockLLMClient({
            'Rate importance 1-10 of factor: market volatility': MockLLMResponse('7'),
            'Rate importance 1-10 of factor: company stability': MockLLMResponse('9')
        })
        
        yaml_rules = """
rules:
  - id: weighted_risk_assessment
    priority: 100
    condition: "base_risk * PROMPT('Rate importance 1-10 of factor: {risk_factor1}', 'int') / 10 + stability_score * PROMPT('Rate importance 1-10 of factor: {risk_factor2}', 'int') / 10 > risk_threshold"
    actions:
      risk_status: HIGH
      weighted_score: "{{ base_risk * LAST_PROMPT_RESULT / 10 + stability_score * PREVIOUS_PROMPT_RESULT / 10 }}"
      market_weight: "{{ LAST_PROMPT_RESULT }}"
      stability_weight: "{{ PREVIOUS_PROMPT_RESULT }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(
            risk_factor1='market volatility',
            risk_factor2='company stability',
            base_risk=6,
            stability_score=3,
            risk_threshold=5
        ))
        
        # Formula: 6 * 7/10 + 3 * 9/10 = 4.2 + 2.7 = 6.9 > 5
        assert result.verdict['risk_status'] == 'HIGH'
        assert result.verdict['weighted_score'] == pytest.approx(6.9, rel=1e-2)
        assert 'weighted_risk_assessment' in result.fired_rules
    
    def test_ai_sentiment_with_numeric_scoring(self):
        """Test AI sentiment analysis converted to numeric scoring."""
        mock_client = MockLLMClient({
            'Analyze sentiment and rate 1-10: This product is absolutely amazing!': MockLLMResponse('9'),
            'Analyze sentiment and rate 1-10: This product is okay I guess': MockLLMResponse('5'),
            'Analyze sentiment and rate 1-10: This product is terrible': MockLLMResponse('2')
        })
        
        yaml_rules = """
rules:
  - id: positive_feedback
    priority: 100
    condition: "PROMPT('Analyze sentiment and rate 1-10: {feedback}', 'int') >= 8"
    actions:
      sentiment_category: POSITIVE
      follow_up: THANK_CUSTOMER
      sentiment_score: "{{ LAST_PROMPT_RESULT }}"
      
  - id: negative_feedback
    priority: 90
    condition: "PROMPT('Analyze sentiment and rate 1-10: {feedback}', 'int') <= 3"
    actions:
      sentiment_category: NEGATIVE
      follow_up: ESCALATE_TO_MANAGER
      sentiment_score: "{{ LAST_PROMPT_RESULT }}"
      
  - id: neutral_feedback
    priority: 80
    condition: "PROMPT('Analyze sentiment and rate 1-10: {feedback}', 'int') > 3 and PROMPT('Analyze sentiment and rate 1-10: {feedback}', 'int') < 8"
    actions:
      sentiment_category: NEUTRAL
      follow_up: STANDARD_RESPONSE
      sentiment_score: "{{ LAST_PROMPT_RESULT }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        
        # Positive feedback
        result1 = engine.reason(facts(feedback='This product is absolutely amazing!'))
        assert result1.verdict['sentiment_category'] == 'POSITIVE'
        assert result1.verdict['follow_up'] == 'THANK_CUSTOMER'
        assert result1.verdict['sentiment_score'] == 9
        
        # Negative feedback
        result2 = engine.reason(facts(feedback='This product is terrible'))
        assert result2.verdict['sentiment_category'] == 'NEGATIVE'
        assert result2.verdict['follow_up'] == 'ESCALATE_TO_MANAGER'
        assert result2.verdict['sentiment_score'] == 2
        
        # Neutral feedback
        result3 = engine.reason(facts(feedback='This product is okay I guess'))
        assert result3.verdict['sentiment_category'] == 'NEUTRAL'
        assert result3.verdict['follow_up'] == 'STANDARD_RESPONSE'
        assert result3.verdict['sentiment_score'] == 5


class TestHybridAIComplexScenarios:
    """Test complex real-world hybrid AI scenarios."""
    
    def test_fraud_detection_hybrid(self):
        """Test fraud detection using AI + rule-based logic."""
        mock_client = MockLLMClient({
            'Rate transaction suspicion 1-10: Large cash withdrawal at 3am in foreign country': MockLLMResponse('9'),
            'Rate transaction suspicion 1-10: Small coffee purchase at local cafe': MockLLMResponse('1')
        })
        
        yaml_rules = """
rules:
  - id: high_fraud_risk
    priority: 100
    condition: "PROMPT('Rate transaction suspicion 1-10: {transaction_description}', 'int') * risk_multiplier + location_risk > fraud_threshold"
    actions:
      fraud_alert: true
      block_transaction: true
      ai_suspicion: "{{ LAST_PROMPT_RESULT }}"
      total_risk_score: "{{ LAST_PROMPT_RESULT * risk_multiplier + location_risk }}"
      action: BLOCK_AND_INVESTIGATE
      
  - id: low_fraud_risk
    priority: 90
    condition: "PROMPT('Rate transaction suspicion 1-10: {transaction_description}', 'int') * risk_multiplier + location_risk <= fraud_threshold"
    actions:
      fraud_alert: false
      block_transaction: false
      ai_suspicion: "{{ LAST_PROMPT_RESULT }}"
      total_risk_score: "{{ LAST_PROMPT_RESULT * risk_multiplier + location_risk }}"
      action: ALLOW_TRANSACTION
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        
        # High risk transaction
        result1 = engine.reason(facts(
            transaction_description='Large cash withdrawal at 3am in foreign country',
            risk_multiplier=2,
            location_risk=3,
            fraud_threshold=15
        ))
        
        # AI suspicion (9) * multiplier (2) + location risk (3) = 21 > 15
        assert result1.verdict['fraud_alert'] is True
        assert result1.verdict['block_transaction'] is True
        assert result1.verdict['ai_suspicion'] == 9
        assert result1.verdict['total_risk_score'] == 21
        assert result1.verdict['action'] == 'BLOCK_AND_INVESTIGATE'
        
        # Low risk transaction
        result2 = engine.reason(facts(
            transaction_description='Small coffee purchase at local cafe',
            risk_multiplier=2,
            location_risk=1,
            fraud_threshold=15
        ))
        
        # AI suspicion (1) * multiplier (2) + location risk (1) = 3 <= 15
        assert result2.verdict['fraud_alert'] is False
        assert result2.verdict['block_transaction'] is False
        assert result2.verdict['ai_suspicion'] == 1
        assert result2.verdict['total_risk_score'] == 3
        assert result2.verdict['action'] == 'ALLOW_TRANSACTION'
    
    def test_loan_approval_hybrid(self):
        """Test loan approval using AI assessment + financial calculations."""
        mock_client = MockLLMClient({
            'Assess borrower profile 1-10: Engineer, 5 years experience, stable employment': MockLLMResponse('8'),
            'Assess borrower profile 1-10: Unemployed, poor credit history': MockLLMResponse('2')
        })
        
        yaml_rules = """
rules:
  - id: loan_approval
    priority: 100
    condition: "PROMPT('Assess borrower profile 1-10: {borrower_profile}', 'int') + credit_score_bonus >= approval_threshold and debt_to_income_ratio < 0.4"
    actions:
      loan_approved: true
      loan_amount: "{{ (LAST_PROMPT_RESULT + credit_score_bonus) * 10000 }}"
      interest_rate: "{{ 0.05 + (10 - (LAST_PROMPT_RESULT + credit_score_bonus)) * 0.005 }}"
      ai_assessment: "{{ LAST_PROMPT_RESULT }}"
      total_score: "{{ LAST_PROMPT_RESULT + credit_score_bonus }}"
      decision: APPROVED
      
  - id: loan_denial
    priority: 90
    condition: "PROMPT('Assess borrower profile 1-10: {borrower_profile}', 'int') + credit_score_bonus < approval_threshold or debt_to_income_ratio >= 0.4"
    actions:
      loan_approved: false
      loan_amount: 0
      interest_rate: 0
      ai_assessment: "{{ LAST_PROMPT_RESULT }}"
      total_score: "{{ LAST_PROMPT_RESULT + credit_score_bonus }}"
      decision: DENIED
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        
        # Approve loan
        result1 = engine.reason(facts(
            borrower_profile='Engineer, 5 years experience, stable employment',
            credit_score_bonus=2,
            approval_threshold=9,
            debt_to_income_ratio=0.3
        ))
        
        # AI score (8) + bonus (2) = 10 >= 9 and DTI (0.3) < 0.4
        assert result1.verdict['loan_approved'] is True
        assert result1.verdict['loan_amount'] == 100000  # 10 * 10000
        assert result1.verdict['interest_rate'] == 0.05  # 0.05 + (10-10) * 0.005
        assert result1.verdict['ai_assessment'] == 8
        assert result1.verdict['total_score'] == 10
        assert result1.verdict['decision'] == 'APPROVED'
        
        # Deny loan
        result2 = engine.reason(facts(
            borrower_profile='Unemployed, poor credit history',
            credit_score_bonus=1,
            approval_threshold=9,
            debt_to_income_ratio=0.3
        ))
        
        # AI score (2) + bonus (1) = 3 < 9
        assert result2.verdict['loan_approved'] is False
        assert result2.verdict['loan_amount'] == 0
        assert result2.verdict['ai_assessment'] == 2
        assert result2.verdict['total_score'] == 3
        assert result2.verdict['decision'] == 'DENIED'
    
    def test_investment_portfolio_rebalancing(self):
        """Test investment portfolio rebalancing with AI market analysis."""
        mock_client = MockLLMClient({
            'Rate market outlook 1-10 for tech sector': MockLLMResponse('7'),
            'Rate market outlook 1-10 for healthcare sector': MockLLMResponse('8'),
            'Rate market outlook 1-10 for energy sector': MockLLMResponse('4')
        })
        
        yaml_rules = """
rules:
  - id: increase_allocation
    priority: 100
    condition: "PROMPT('Rate market outlook 1-10 for {sector} sector', 'int') >= 7"
    actions:
      allocation_change: INCREASE
      new_allocation: "{{ current_allocation + (LAST_PROMPT_RESULT - 5) * 2 }}"
      ai_outlook: "{{ LAST_PROMPT_RESULT }}"
      confidence_level: HIGH
      
  - id: decrease_allocation
    priority: 90
    condition: "PROMPT('Rate market outlook 1-10 for {sector} sector', 'int') <= 4"
    actions:
      allocation_change: DECREASE
      new_allocation: "{{ current_allocation - (5 - LAST_PROMPT_RESULT) * 2 }}"
      ai_outlook: "{{ LAST_PROMPT_RESULT }}"
      confidence_level: LOW
      
  - id: maintain_allocation
    priority: 80
    condition: "PROMPT('Rate market outlook 1-10 for {sector} sector', 'int') > 4 and PROMPT('Rate market outlook 1-10 for {sector} sector', 'int') < 7"
    actions:
      allocation_change: MAINTAIN
      new_allocation: "{{ current_allocation }}"
      ai_outlook: "{{ LAST_PROMPT_RESULT }}"
      confidence_level: MEDIUM
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        
        # Increase tech allocation (AI outlook: 7)
        result1 = engine.reason(facts(sector='tech', current_allocation=20))
        assert result1.verdict['allocation_change'] == 'INCREASE'
        assert result1.verdict['new_allocation'] == 24  # 20 + (7-5)*2
        assert result1.verdict['ai_outlook'] == 7
        assert result1.verdict['confidence_level'] == 'HIGH'
        
        # Decrease energy allocation (AI outlook: 4)
        result2 = engine.reason(facts(sector='energy', current_allocation=15))
        assert result2.verdict['allocation_change'] == 'DECREASE'
        assert result2.verdict['new_allocation'] == 13  # 15 - (5-4)*2
        assert result2.verdict['ai_outlook'] == 4
        assert result2.verdict['confidence_level'] == 'LOW'


class TestHybridAIErrorHandling:
    """Test error handling in hybrid AI scenarios."""
    
    def test_ai_failure_with_fallback(self):
        """Test graceful handling when AI fails but arithmetic continues."""
        mock_client = Mock()
        mock_client.complete.side_effect = Exception("AI service unavailable")
        
        yaml_rules = """
rules:
  - id: ai_dependent_rule
    priority: 100
    condition: "PROMPT('Rate: {item}', 'int') + bonus > 10"
    actions:
      ai_result: true
      
  - id: fallback_rule
    priority: 90
    condition: "fallback_score + bonus > 10"
    actions:
      fallback_result: true
      total: "{{ fallback_score + bonus }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(item='test', bonus=5, fallback_score=8))
        
        # AI rule should fail, fallback should succeed
        assert 'ai_dependent_rule' not in result.fired_rules
        assert 'fallback_rule' in result.fired_rules
        assert result.verdict['fallback_result'] is True
        assert result.verdict['total'] == 13
    
    def test_partial_ai_failure(self):
        """Test when some AI calls succeed and others fail."""
        mock_client = Mock()
        mock_client.complete.side_effect = [
            MockLLMResponse('8'),  # First call succeeds
            Exception("Second call fails")  # Second call fails
        ]
        
        yaml_rules = """
rules:
  - id: mixed_ai_rule
    priority: 100
    condition: "PROMPT('Rate first: {item}', 'int') > 5"
    actions:
      first_success: true
      first_score: "{{ LAST_PROMPT_RESULT }}"
      
  - id: second_ai_rule
    priority: 90
    condition: "PROMPT('Rate second: {item}', 'int') > 5"
    actions:
      second_success: true
      second_score: "{{ LAST_PROMPT_RESULT }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(item='test'))
        
        # First rule should succeed, second should fail
        assert 'mixed_ai_rule' in result.fired_rules
        assert 'second_ai_rule' not in result.fired_rules
        assert result.verdict['first_success'] is True
        assert result.verdict['first_score'] == 8
        assert 'second_success' not in result.verdict
    
    def test_ai_type_conversion_errors(self):
        """Test handling of AI type conversion errors in arithmetic."""
        mock_client = MockLLMClient({
            'Rate numeric: test': MockLLMResponse('not_a_number'),
            'Rate valid: test': MockLLMResponse('7')
        })
        
        yaml_rules = """
rules:
  - id: invalid_conversion_rule
    priority: 100
    condition: "PROMPT('Rate numeric: {item}', 'int') + bonus > 10"
    actions:
      invalid_result: true
      
  - id: valid_conversion_rule
    priority: 90
    condition: "PROMPT('Rate valid: {item}', 'int') + bonus > 10"
    actions:
      valid_result: true
      total: "{{ LAST_PROMPT_RESULT + bonus }}"
"""
        
        engine = Engine.from_yaml(yaml_rules, llm_client=mock_client)
        result = engine.reason(facts(item='test', bonus=5))
        
        # Invalid conversion rule should fail, valid should succeed
        assert 'invalid_conversion_rule' not in result.fired_rules
        assert 'valid_conversion_rule' in result.fired_rules
        assert result.verdict['valid_result'] is True
        assert result.verdict['total'] == 12  # 7 + 5 