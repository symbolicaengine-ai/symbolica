"""
Unit Tests for String Action Values
==================================

Tests for string action value handling, expression detection, and the bug fix
that prevented string literals from becoming None.
"""

import pytest
from symbolica import Engine, facts
from symbolica.core.models import Rule


class TestStringActionValues:
    """Test string action value handling and preservation."""
    
    def test_simple_string_action_values(self):
        """Test that simple string values are preserved correctly."""
        yaml_rules = """
rules:
  - id: string_test
    priority: 100
    condition: "score > 5"
    actions:
      decision: APPROVED
      status: ACTIVE
      category: PREMIUM
      result: SUCCESS
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(score=7))
        
        # All string values should be preserved exactly
        assert result.verdict['decision'] == 'APPROVED'
        assert result.verdict['status'] == 'ACTIVE'
        assert result.verdict['category'] == 'PREMIUM'
        assert result.verdict['result'] == 'SUCCESS'
        
        # None of them should be None
        assert result.verdict['decision'] is not None
        assert result.verdict['status'] is not None
        assert result.verdict['category'] is not None
        assert result.verdict['result'] is not None
    
    def test_mixed_action_value_types(self):
        """Test mixed action value types - strings, numbers, booleans."""
        yaml_rules = """
rules:
  - id: mixed_test
    priority: 100
    condition: "score > 5"
    actions:
      decision: APPROVED         # String
      approved: true             # Boolean
      confidence: 0.95           # Float
      priority: 1                # Integer
      status: "ACTIVE"           # Quoted string
      category: 'PREMIUM'        # Single quoted string
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(score=7))
        
        # Check all types are preserved correctly
        assert result.verdict['decision'] == 'APPROVED'
        assert result.verdict['approved'] is True
        assert result.verdict['confidence'] == 0.95
        assert result.verdict['priority'] == 1
        assert result.verdict['status'] == 'ACTIVE'
        assert result.verdict['category'] == 'PREMIUM'
    
    def test_string_values_with_special_characters(self):
        """Test string values with special characters and spaces."""
        yaml_rules = """
rules:
  - id: special_chars_test
    priority: 100
    condition: "score > 5"
    actions:
      message: "Processing complete - success!"
      path: "/home/user/documents"
      url: "https://example.com/api"
      email: "user@example.com"
      phone: "+1-555-123-4567"
      description: "Multi-word description with spaces"
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(score=7))
        
        # All special strings should be preserved
        assert result.verdict['message'] == 'Processing complete - success!'
        assert result.verdict['path'] == '/home/user/documents'
        assert result.verdict['url'] == 'https://example.com/api'
        assert result.verdict['email'] == 'user@example.com'
        assert result.verdict['phone'] == '+1-555-123-4567'
        assert result.verdict['description'] == 'Multi-word description with spaces'
    
    def test_business_decision_strings(self):
        """Test realistic business decision strings."""
        yaml_rules = """
rules:
  - id: approve_loan
    priority: 100
    condition: "credit_score > 700"
    actions:
      decision: APPROVE
      reason: HIGH_CREDIT_SCORE
      next_step: FUND_LOAN
      
  - id: reject_loan
    priority: 90
    condition: "credit_score < 600"
    actions:
      decision: REJECT
      reason: LOW_CREDIT_SCORE
      next_step: SEND_REJECTION_LETTER
      
  - id: review_loan
    priority: 80
    condition: "credit_score >= 600 and credit_score <= 700"
    actions:
      decision: REVIEW
      reason: MODERATE_CREDIT_SCORE
      next_step: MANUAL_REVIEW
"""
        
        engine = Engine.from_yaml(yaml_rules)
        
        # Test approval case
        result1 = engine.reason(facts(credit_score=750))
        assert result1.verdict['decision'] == 'APPROVE'
        assert result1.verdict['reason'] == 'HIGH_CREDIT_SCORE'
        assert result1.verdict['next_step'] == 'FUND_LOAN'
        
        # Test rejection case
        result2 = engine.reason(facts(credit_score=550))
        assert result2.verdict['decision'] == 'REJECT'
        assert result2.verdict['reason'] == 'LOW_CREDIT_SCORE'
        assert result2.verdict['next_step'] == 'SEND_REJECTION_LETTER'
        
        # Test review case
        result3 = engine.reason(facts(credit_score=650))
        assert result3.verdict['decision'] == 'REVIEW'
        assert result3.verdict['reason'] == 'MODERATE_CREDIT_SCORE'
        assert result3.verdict['next_step'] == 'MANUAL_REVIEW'


class TestExpressionDetection:
    """Test the _is_expression method logic."""
    
    def test_strings_not_detected_as_expressions(self):
        """Test that plain strings are not detected as expressions."""
        yaml_rules = """
rules:
  - id: string_detection_test
    priority: 100
    condition: "value > 5"
    actions:
      # These should NOT be detected as expressions
      decision: APPROVED
      status: ACTIVE
      category: PREMIUM
      result: SUCCESS
      message: PROCESSING_COMPLETE
      action: SEND_EMAIL
      type: NOTIFICATION
      level: HIGH
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(value=7))
        
        # All values should be preserved as strings, not None
        expected_values = {
            'decision': 'APPROVED',
            'status': 'ACTIVE',
            'category': 'PREMIUM',
            'result': 'SUCCESS',
            'message': 'PROCESSING_COMPLETE',
            'action': 'SEND_EMAIL',
            'type': 'NOTIFICATION',
            'level': 'HIGH'
        }
        
        for key, expected in expected_values.items():
            assert result.verdict[key] == expected
            assert result.verdict[key] is not None
    
    def test_expressions_detected_correctly(self):
        """Test that real expressions are detected and evaluated."""
        yaml_rules = """
rules:
  - id: expression_test
    priority: 100
    condition: "base_score > 5"
    actions:
      # These SHOULD be detected as expressions
      calculated_score: "{{ base_score + 10 }}"
      multiplied_score: "{{ base_score * 2 }}"
      comparison_result: "{{ base_score > 10 }}"
      arithmetic_result: "{{ (base_score + 5) * 2 }}"
      template_string: "Score is {{ base_score }}"
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(base_score=8))
        
        # Template expressions should be evaluated
        assert result.verdict['calculated_score'] == 18  # 8 + 10
        assert result.verdict['multiplied_score'] == 16   # 8 * 2
        assert result.verdict['comparison_result'] is False  # 8 > 10 = False
        assert result.verdict['arithmetic_result'] == 26     # (8 + 5) * 2 = 26
        assert result.verdict['template_string'] == 'Score is 8'
    
    def test_arithmetic_expressions_detected(self):
        """Test that arithmetic expressions are detected and evaluated."""
        yaml_rules = """
rules:
  - id: arithmetic_test
    priority: 100
    condition: "value > 0"
    actions:
      # Arithmetic expressions
      sum_result: value + 10
      difference: value - 5
      product: value * 3
      quotient: value / 2
      power: value ** 2
      # But not plain strings
      status: CALCULATED
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(value=6))
        
        # Arithmetic should be evaluated
        assert result.verdict['sum_result'] == 16    # 6 + 10
        assert result.verdict['difference'] == 1     # 6 - 5
        assert result.verdict['product'] == 18       # 6 * 3
        assert result.verdict['quotient'] == 3.0     # 6 / 2
        assert result.verdict['power'] == 36         # 6 ** 2
        
        # String should be preserved
        assert result.verdict['status'] == 'CALCULATED'
    
    def test_function_calls_detected(self):
        """Test that function calls are detected and evaluated."""
        yaml_rules = """
rules:
  - id: function_test
    priority: 100
    condition: "numbers != None"
    actions:
      # Function calls - should be evaluated
      total: sum(numbers)
      count: len(numbers)
      absolute_value: abs(negative_value)
      # Plain strings - should be preserved
      operation: CALCULATED
      method: FUNCTION_CALL
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(numbers=[1, 2, 3, 4, 5], negative_value=-10))
        
        # Function calls should be evaluated
        assert result.verdict['total'] == 15        # sum([1,2,3,4,5])
        assert result.verdict['count'] == 5         # len([1,2,3,4,5])
        assert result.verdict['absolute_value'] == 10  # abs(-10)
        
        # Strings should be preserved
        assert result.verdict['operation'] == 'CALCULATED'
        assert result.verdict['method'] == 'FUNCTION_CALL'
    
    def test_comparison_expressions_detected(self):
        """Test that comparison expressions are detected and evaluated."""
        yaml_rules = """
rules:
  - id: comparison_test
    priority: 100
    condition: "score > 0"
    actions:
      # Comparison expressions - should be evaluated
      is_high: score > 80
      is_passing: score >= 60
      is_perfect: score == 100
      is_failing: score < 40
      # Plain strings - should be preserved
      grade: CALCULATED
      status: EVALUATED
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(score=85))
        
        # Comparisons should be evaluated
        assert result.verdict['is_high'] is True      # 85 > 80
        assert result.verdict['is_passing'] is True   # 85 >= 60
        assert result.verdict['is_perfect'] is False  # 85 == 100
        assert result.verdict['is_failing'] is False  # 85 < 40
        
        # Strings should be preserved
        assert result.verdict['grade'] == 'CALCULATED'
        assert result.verdict['status'] == 'EVALUATED'


class TestActionValueEvaluation:
    """Test the _evaluate_action_value method."""
    
    def test_action_value_evaluation_mixed_types(self):
        """Test evaluation of mixed action value types."""
        yaml_rules = """
rules:
  - id: mixed_evaluation_test
    priority: 100
    condition: "base_value > 0"
    actions:
      # Literals - should be preserved
      string_literal: APPROVED
      number_literal: 42
      boolean_literal: true
      
      # Expressions - should be evaluated
      calculated: base_value + 100
      doubled: base_value * 2
      template: "Value is {{ base_value }}"
      
      # Complex expressions
      complex_calc: (base_value + 10) * 2
      comparison: base_value > 50
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(base_value=25))
        
        # Literals should be preserved
        assert result.verdict['string_literal'] == 'APPROVED'
        assert result.verdict['number_literal'] == 42
        assert result.verdict['boolean_literal'] is True
        
        # Expressions should be evaluated
        assert result.verdict['calculated'] == 125      # 25 + 100
        assert result.verdict['doubled'] == 50          # 25 * 2
        assert result.verdict['template'] == 'Value is 25'
        
        # Complex expressions should be evaluated
        assert result.verdict['complex_calc'] == 70     # (25 + 10) * 2
        assert result.verdict['comparison'] is False    # 25 > 50
    
    def test_action_value_error_handling(self):
        """Test error handling in action value evaluation."""
        yaml_rules = """
rules:
  - id: error_handling_test
    priority: 100
    condition: "value > 0"
    actions:
      # Valid expression
      valid_calc: value + 10
      # Invalid expression (should fallback to original)
      invalid_calc: value / unknown_field
      # String literal (should be preserved)
      status: PROCESSED
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(value=5))
        
        # Valid expression should be evaluated
        assert result.verdict['valid_calc'] == 15  # 5 + 10
        
        # Invalid expression should fallback to original string
        assert result.verdict['invalid_calc'] == 'value / unknown_field'
        
        # String literal should be preserved
        assert result.verdict['status'] == 'PROCESSED'
    
    def test_action_value_with_missing_fields(self):
        """Test action value evaluation with missing fields."""
        yaml_rules = """
rules:
  - id: missing_field_test
    priority: 100
    condition: "present_field > 0"
    actions:
      # Expression with present field
      with_present: present_field * 2
      # Expression with missing field
      with_missing: missing_field + 10
      # String literal
      status: CALCULATED
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(present_field=7))
        
        # Expression with present field should work
        assert result.verdict['with_present'] == 14  # 7 * 2
        
        # Expression with missing field should fallback
        assert result.verdict['with_missing'] == 'missing_field + 10'
        
        # String literal should be preserved
        assert result.verdict['status'] == 'CALCULATED'


class TestRegressionTests:
    """Regression tests for the string action value bug."""
    
    def test_string_action_value_bug_regression(self):
        """Test that the original bug (strings becoming None) is fixed."""
        yaml_rules = """
rules:
  - id: regression_test
    priority: 100
    condition: "score > 5"
    actions:
      decision: APPROVED
      status: ACTIVE
      category: PREMIUM
      result: SUCCESS
      action: PROCESS
      type: NOTIFICATION
      level: HIGH
      grade: A
      rank: FIRST
      priority: URGENT
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(score=7))
        
        # ALL string values should be preserved, NONE should be None
        expected_strings = [
            'APPROVED', 'ACTIVE', 'PREMIUM', 'SUCCESS', 'PROCESS',
            'NOTIFICATION', 'HIGH', 'A', 'FIRST', 'URGENT'
        ]
        
        actual_values = list(result.verdict.values())
        
        # Check that all expected strings are present
        for expected in expected_strings:
            assert expected in actual_values, f"Expected '{expected}' not found in {actual_values}"
        
        # Check that no values are None
        for key, value in result.verdict.items():
            assert value is not None, f"Action '{key}' should not be None, got {value}"
    
    def test_investment_decision_regression(self):
        """Test the specific investment decision example that was failing."""
        yaml_rules = """
rules:
  - id: investment_decision
    priority: 100
    condition: "confidence_score > 7"
    actions:
      decision: INVEST
      reason: HIGH_CONFIDENCE
      next_action: EXECUTE_TRADE
      
  - id: rejection_decision
    priority: 90
    condition: "confidence_score < 4"
    actions:
      decision: REJECT
      reason: LOW_CONFIDENCE
      next_action: SKIP_TRADE
"""
        
        engine = Engine.from_yaml(yaml_rules)
        
        # Test investment scenario
        result1 = engine.reason(facts(confidence_score=8))
        assert result1.verdict['decision'] == 'INVEST'
        assert result1.verdict['reason'] == 'HIGH_CONFIDENCE'
        assert result1.verdict['next_action'] == 'EXECUTE_TRADE'
        
        # Test rejection scenario
        result2 = engine.reason(facts(confidence_score=2))
        assert result2.verdict['decision'] == 'REJECT'
        assert result2.verdict['reason'] == 'LOW_CONFIDENCE'
        assert result2.verdict['next_action'] == 'SKIP_TRADE'
        
        # Ensure no None values
        for key, value in result1.verdict.items():
            assert value is not None, f"Investment decision '{key}' should not be None"
        for key, value in result2.verdict.items():
            assert value is not None, f"Rejection decision '{key}' should not be None"
    
    def test_hybrid_ai_arithmetic_regression(self):
        """Test that hybrid AI + arithmetic works with proper string handling."""
        yaml_rules = """
rules:
  - id: hybrid_rule
    priority: 100
    condition: "ai_score + market_bonus > 12"
    actions:
      should_invest: true
      decision: INVEST
      total_score: "{{ ai_score + market_bonus }}"
      reason: MEETS_THRESHOLD
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(ai_score=9, market_bonus=4))
        
        # Boolean should be preserved
        assert result.verdict['should_invest'] is True
        
        # String should be preserved
        assert result.verdict['decision'] == 'INVEST'
        assert result.verdict['reason'] == 'MEETS_THRESHOLD'
        
        # Template should be evaluated
        assert result.verdict['total_score'] == 13  # 9 + 4
        
        # No None values
        for key, value in result.verdict.items():
            assert value is not None, f"Hybrid rule '{key}' should not be None"
    
    def test_edge_case_string_patterns(self):
        """Test edge cases that might trigger incorrect expression detection."""
        yaml_rules = """
rules:
  - id: edge_case_test
    priority: 100
    condition: "value > 0"
    actions:
      # These look like they might be expressions but should be strings
      version: v1.0.0
      id: user_123
      code: ABC-123
      reference: REF-2023-001
      constant: TRUE
      flag: ON
      mode: AUTO
      level: L1
      grade: A+
      score: 100%
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(value=1))
        
        # All should be preserved as strings
        expected_values = {
            'version': 'v1.0.0',
            'id': 'user_123',
            'code': 'ABC-123',
            'reference': 'REF-2023-001',
            'constant': 'TRUE',
            'flag': 'ON',
            'mode': 'AUTO',
            'level': 'L1',
            'grade': 'A+',
            'score': '100%'
        }
        
        for key, expected in expected_values.items():
            assert result.verdict[key] == expected
            assert result.verdict[key] is not None 