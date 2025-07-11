"""
Unit Tests for Expression Actions
================================

Tests for expression evaluation in rule actions, including template variables,
arithmetic expressions, and the _evaluate_action_value method.
"""

import pytest
from symbolica import Engine, facts
from symbolica.core.models import Rule


class TestTemplateVariables:
    """Test template variable evaluation in actions."""
    
    def test_basic_template_variables(self):
        """Test basic template variable substitution."""
        yaml_rules = """
rules:
  - id: template_test
    priority: 100
    condition: "score > 5"
    actions:
      score_doubled: "{{ score * 2 }}"
      score_plus_ten: "{{ score + 10 }}"
      original_score: "{{ score }}"
      calculated_bonus: "{{ score * 0.1 }}"
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(score=8))
        
        # Template variables should be evaluated
        assert result.verdict['score_doubled'] == 16    # 8 * 2
        assert result.verdict['score_plus_ten'] == 18   # 8 + 10
        assert result.verdict['original_score'] == 8    # 8
        assert result.verdict['calculated_bonus'] == pytest.approx(0.8, rel=1e-2)  # 8 * 0.1
    
    def test_complex_template_expressions(self):
        """Test complex mathematical expressions in templates."""
        yaml_rules = """
rules:
  - id: complex_template_test
    priority: 100
    condition: "base_value > 0"
    actions:
      compound_calc: "{{ (base_value + 5) * 2 - 3 }}"
      power_calc: "{{ base_value ** 2 }}"
      division_calc: "{{ base_value / 2 }}"
      modulo_calc: "{{ base_value % 3 }}"
      nested_calc: "{{ ((base_value + 1) * 2) / 3 }}"
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(base_value=7))
        
        # Complex calculations should be evaluated
        assert result.verdict['compound_calc'] == 21      # (7 + 5) * 2 - 3 = 21
        assert result.verdict['power_calc'] == 49         # 7 ** 2 = 49
        assert result.verdict['division_calc'] == 3.5     # 7 / 2 = 3.5
        assert result.verdict['modulo_calc'] == 1         # 7 % 3 = 1
        assert result.verdict['nested_calc'] == pytest.approx(5.33, rel=1e-2)  # ((7+1)*2)/3 = 5.33
    
    def test_template_with_multiple_variables(self):
        """Test templates with multiple variables."""
        yaml_rules = """
rules:
  - id: multi_var_template_test
    priority: 100
    condition: "a > 0 and b > 0"
    actions:
      sum_result: "{{ a + b }}"
      product_result: "{{ a * b }}"
      weighted_average: "{{ (a * weight_a + b * weight_b) / (weight_a + weight_b) }}"
      comparison_result: "{{ a > b }}"
      string_template: "a={{ a }}, b={{ b }}"
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(a=5, b=3, weight_a=2, weight_b=1))
        
        # Multi-variable templates should be evaluated
        assert result.verdict['sum_result'] == 8          # 5 + 3
        assert result.verdict['product_result'] == 15     # 5 * 3
        assert result.verdict['weighted_average'] == pytest.approx(4.33, rel=1e-2)  # (5*2+3*1)/(2+1)
        assert result.verdict['comparison_result'] is True  # 5 > 3
        assert result.verdict['string_template'] == 'a=5, b=3'
    
    def test_template_with_conditionals(self):
        """Test templates with conditional expressions."""
        yaml_rules = """
rules:
  - id: conditional_template_test
    priority: 100
    condition: "score > 0"
    actions:
      grade_numeric: "{{ score }}"
      is_passing: "{{ score >= 60 }}"
      bonus_eligible: "{{ score > 80 }}"
      score_category: "{{ 'high' if score > 90 else 'medium' if score > 70 else 'low' }}"
"""
        
        engine = Engine.from_yaml(yaml_rules)
        
        # Test high score
        result1 = engine.reason(facts(score=95))
        assert result1.verdict['grade_numeric'] == 95
        assert result1.verdict['is_passing'] is True
        assert result1.verdict['bonus_eligible'] is True
        assert result1.verdict['score_category'] == 'high'
        
        # Test medium score
        result2 = engine.reason(facts(score=75))
        assert result2.verdict['grade_numeric'] == 75
        assert result2.verdict['is_passing'] is True
        assert result2.verdict['bonus_eligible'] is False
        assert result2.verdict['score_category'] == 'medium'
        
        # Test low score
        result3 = engine.reason(facts(score=45))
        assert result3.verdict['grade_numeric'] == 45
        assert result3.verdict['is_passing'] is False
        assert result3.verdict['bonus_eligible'] is False
        assert result3.verdict['score_category'] == 'low'
    
    def test_template_with_functions(self):
        """Test templates with built-in functions."""
        yaml_rules = """
rules:
  - id: function_template_test
    priority: 100
    condition: "numbers != None"
    actions:
      list_sum: "{{ sum(numbers) }}"
      list_length: "{{ len(numbers) }}"
      max_value: "{{ max(numbers) }}"
      min_value: "{{ min(numbers) }}"
      average: "{{ sum(numbers) / len(numbers) }}"
      abs_value: "{{ abs(negative_number) }}"
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(numbers=[1, 5, 3, 9, 2], negative_number=-15))
        
        # Function calls should be evaluated
        assert result.verdict['list_sum'] == 20           # sum([1,5,3,9,2])
        assert result.verdict['list_length'] == 5         # len([1,5,3,9,2])
        assert result.verdict['max_value'] == 9           # max([1,5,3,9,2])
        assert result.verdict['min_value'] == 1           # min([1,5,3,9,2])
        assert result.verdict['average'] == 4.0           # 20 / 5
        assert result.verdict['abs_value'] == 15          # abs(-15)


class TestArithmeticExpressions:
    """Test arithmetic expression evaluation in actions."""
    
    def test_basic_arithmetic_actions(self):
        """Test basic arithmetic operations in actions."""
        yaml_rules = """
rules:
  - id: arithmetic_test
    priority: 100
    condition: "value > 0"
    actions:
      addition: value + 10
      subtraction: value - 5
      multiplication: value * 3
      division: value / 2
      power: value ** 2
      string_literal: CALCULATED
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(value=8))
        
        # Arithmetic expressions should be evaluated
        assert result.verdict['addition'] == 18          # 8 + 10
        assert result.verdict['subtraction'] == 3        # 8 - 5
        assert result.verdict['multiplication'] == 24    # 8 * 3
        assert result.verdict['division'] == 4.0         # 8 / 2
        assert result.verdict['power'] == 64             # 8 ** 2
        
        # String literal should be preserved
        assert result.verdict['string_literal'] == 'CALCULATED'
    
    def test_arithmetic_with_multiple_fields(self):
        """Test arithmetic operations with multiple fields."""
        yaml_rules = """
rules:
  - id: multi_field_arithmetic_test
    priority: 100
    condition: "a > 0 and b > 0"
    actions:
      sum_ab: a + b
      product_ab: a * b
      difference_ab: a - b
      ratio_ab: a / b
      combined_calc: (a + b) * multiplier
      status: COMPUTED
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(a=12, b=4, multiplier=2))
        
        # Multi-field arithmetic should be evaluated
        assert result.verdict['sum_ab'] == 16            # 12 + 4
        assert result.verdict['product_ab'] == 48        # 12 * 4
        assert result.verdict['difference_ab'] == 8      # 12 - 4
        assert result.verdict['ratio_ab'] == 3.0         # 12 / 4
        assert result.verdict['combined_calc'] == 32     # (12 + 4) * 2
        
        # String literal should be preserved
        assert result.verdict['status'] == 'COMPUTED'
    
    def test_complex_arithmetic_expressions(self):
        """Test complex arithmetic expressions."""
        yaml_rules = """
rules:
  - id: complex_arithmetic_test
    priority: 100
    condition: "base > 0"
    actions:
      polynomial: base * base * base + 2 * base * base + base + 1
      nested_operations: ((base + 1) * (base - 1)) / 2
      percentage_calc: (base / total) * 100
      compound_interest: principal * (1 + rate) ** years
      result_type: COMPLEX_CALCULATION
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(base=3, total=50, principal=1000, rate=0.05, years=2))
        
        # Complex arithmetic should be evaluated
        assert result.verdict['polynomial'] == 40        # 3^3 + 2*3^2 + 3 + 1 = 27 + 18 + 3 + 1
        assert result.verdict['nested_operations'] == 4.0  # ((3+1)*(3-1))/2 = (4*2)/2 = 4
        assert result.verdict['percentage_calc'] == 6.0   # (3/50)*100 = 6
        assert result.verdict['compound_interest'] == pytest.approx(1102.5, rel=1e-2)  # 1000*(1.05)^2
        
        # String literal should be preserved
        assert result.verdict['result_type'] == 'COMPLEX_CALCULATION'
    
    def test_arithmetic_with_boolean_results(self):
        """Test arithmetic expressions that result in boolean values."""
        yaml_rules = """
rules:
  - id: boolean_arithmetic_test
    priority: 100
    condition: "value > 0"
    actions:
      is_positive: value > 0
      is_even: value % 2 == 0
      is_large: value > 100
      in_range: value >= 10 and value <= 50
      equals_target: value == target
      status: BOOLEAN_TESTED
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(value=24, target=24))
        
        # Boolean arithmetic should be evaluated
        assert result.verdict['is_positive'] is True     # 24 > 0
        assert result.verdict['is_even'] is True         # 24 % 2 == 0
        assert result.verdict['is_large'] is False       # 24 > 100
        assert result.verdict['in_range'] is True        # 24 >= 10 and 24 <= 50
        assert result.verdict['equals_target'] is True   # 24 == 24
        
        # String literal should be preserved
        assert result.verdict['status'] == 'BOOLEAN_TESTED'


class TestExpressionActionEdgeCases:
    """Test edge cases in expression action evaluation."""
    
    def test_expressions_with_missing_fields(self):
        """Test expressions with missing fields."""
        yaml_rules = """
rules:
  - id: missing_field_test
    priority: 100
    condition: "present_field > 0"
    actions:
      # This should work
      valid_calc: present_field * 2
      # This should fallback to original string
      invalid_calc: missing_field + 10
      # This should be preserved
      status: PROCESSED
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(present_field=5))
        
        # Valid calculation should work
        assert result.verdict['valid_calc'] == 10
        
        # Invalid calculation should fallback to original string
        assert result.verdict['invalid_calc'] == 'missing_field + 10'
        
        # String literal should be preserved
        assert result.verdict['status'] == 'PROCESSED'
    
    def test_expressions_with_none_values(self):
        """Test expressions with None values."""
        yaml_rules = """
rules:
  - id: none_value_test
    priority: 100
    condition: "valid_field > 0"
    actions:
      # This should work
      valid_calc: valid_field * 2
      # This should handle None gracefully
      none_calc: none_field + 10
      # This should be preserved
      status: NONE_HANDLED
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(valid_field=7, none_field=None))
        
        # Valid calculation should work
        assert result.verdict['valid_calc'] == 14
        
        # None calculation should fallback to original string
        assert result.verdict['none_calc'] == 'none_field + 10'
        
        # String literal should be preserved
        assert result.verdict['status'] == 'NONE_HANDLED'
    
    def test_expressions_with_type_errors(self):
        """Test expressions that cause type errors."""
        yaml_rules = """
rules:
  - id: type_error_test
    priority: 100
    condition: "number_field > 0"
    actions:
      # This should work
      valid_calc: number_field * 2
      # This should cause a type error and fallback
      type_error_calc: string_field + number_field
      # This should be preserved
      status: TYPE_ERROR_HANDLED
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(number_field=5, string_field='hello'))
        
        # Valid calculation should work
        assert result.verdict['valid_calc'] == 10
        
        # Type error calculation should fallback to original string
        assert result.verdict['type_error_calc'] == 'string_field + number_field'
        
        # String literal should be preserved
        assert result.verdict['status'] == 'TYPE_ERROR_HANDLED'
    
    def test_expressions_with_division_by_zero(self):
        """Test expressions that cause division by zero."""
        yaml_rules = """
rules:
  - id: division_by_zero_test
    priority: 100
    condition: "numerator > 0"
    actions:
      # This should work
      valid_division: numerator / 2
      # This should cause division by zero and fallback
      zero_division: numerator / zero_denominator
      # This should be preserved
      status: DIVISION_ERROR_HANDLED
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(numerator=10, zero_denominator=0))
        
        # Valid division should work
        assert result.verdict['valid_division'] == 5.0
        
        # Zero division should fallback to original string
        assert result.verdict['zero_division'] == 'numerator / zero_denominator'
        
        # String literal should be preserved
        assert result.verdict['status'] == 'DIVISION_ERROR_HANDLED'
    
    def test_mixed_expression_and_literal_actions(self):
        """Test mixing expressions and literals in the same rule."""
        yaml_rules = """
rules:
  - id: mixed_actions_test
    priority: 100
    condition: "value > 0"
    actions:
      # Literals (should be preserved as-is)
      decision: APPROVED
      status: ACTIVE
      category: PREMIUM
      flag: true
      count: 42
      
      # Expressions (should be evaluated)
      calculated_value: value * 2
      is_high: value > 50
      templated_message: "Value is {{ value }}"
      arithmetic_result: (value + 10) / 2
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(value=30))
        
        # Literals should be preserved
        assert result.verdict['decision'] == 'APPROVED'
        assert result.verdict['status'] == 'ACTIVE'
        assert result.verdict['category'] == 'PREMIUM'
        assert result.verdict['flag'] is True
        assert result.verdict['count'] == 42
        
        # Expressions should be evaluated
        assert result.verdict['calculated_value'] == 60    # 30 * 2
        assert result.verdict['is_high'] is False          # 30 > 50
        assert result.verdict['templated_message'] == 'Value is 30'
        assert result.verdict['arithmetic_result'] == 20.0  # (30 + 10) / 2
    
    def test_expression_action_evaluation_order(self):
        """Test that expression actions are evaluated in the correct context."""
        yaml_rules = """
rules:
  - id: evaluation_order_test
    priority: 100
    condition: "base_value > 0"
    facts:
      # These are intermediate facts available to other rules
      doubled_value: base_value * 2
      incremented_value: base_value + 1
    actions:
      # These should have access to both original and intermediate facts
      final_calc: doubled_value + incremented_value
      original_plus_doubled: base_value + doubled_value
      template_with_facts: "Base: {{ base_value }}, Doubled: {{ doubled_value }}"
      status: EVALUATION_COMPLETE
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(base_value=5))
        
        # Final calculations should use intermediate facts
        assert result.verdict['final_calc'] == 16         # (5*2) + (5+1) = 10 + 6 = 16
        assert result.verdict['original_plus_doubled'] == 15  # 5 + (5*2) = 5 + 10 = 15
        assert result.verdict['template_with_facts'] == 'Base: 5, Doubled: 10'
        
        # String literal should be preserved
        assert result.verdict['status'] == 'EVALUATION_COMPLETE'
        
        # Intermediate facts should also be accessible
        assert result.verdict['doubled_value'] == 10      # From facts
        assert result.verdict['incremented_value'] == 6   # From facts


class TestTemplateStringHandling:
    """Test template string handling and mixed content."""
    
    def test_template_strings_with_mixed_content(self):
        """Test template strings with mixed text and expressions."""
        yaml_rules = """
rules:
  - id: mixed_template_test
    priority: 100
    condition: "user_name != None"
    actions:
      greeting: "Hello {{ user_name }}, your score is {{ score }}"
      summary: "User {{ user_name }} scored {{ score }}/100 ({{ (score/100)*100 }}%)"
      status_message: "Processing complete for {{ user_name }}"
      calculation_result: "{{ score * 2 }}"
      plain_string: "This is just text"
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(user_name='Alice', score=85))
        
        # Mixed template strings should be evaluated
        assert result.verdict['greeting'] == 'Hello Alice, your score is 85'
        assert result.verdict['summary'] == 'User Alice scored 85/100 (85.0%)'
        assert result.verdict['status_message'] == 'Processing complete for Alice'
        assert result.verdict['calculation_result'] == 85  # Pure expression becomes number
        
        # Plain string should be preserved
        assert result.verdict['plain_string'] == 'This is just text'
    
    def test_template_with_special_characters(self):
        """Test templates with special characters and escaping."""
        yaml_rules = """
rules:
  - id: special_char_template_test
    priority: 100
    condition: "amount > 0"
    actions:
      currency_display: "Amount: ${{ amount }}"
      percentage_display: "{{ (amount/total)*100 }}% of total"
      json_like: '{"amount": {{ amount }}, "total": {{ total }}}'
      email_template: "Dear customer, your balance is ${{ amount }}"
      path_template: "/users/{{ user_id }}/accounts/{{ account_id }}"
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(amount=150, total=500, user_id=123, account_id=456))
        
        # Special character templates should be evaluated
        assert result.verdict['currency_display'] == 'Amount: $150'
        assert result.verdict['percentage_display'] == '30.0% of total'
        assert result.verdict['json_like'] == '{"amount": 150, "total": 500}'
        assert result.verdict['email_template'] == 'Dear customer, your balance is $150'
        assert result.verdict['path_template'] == '/users/123/accounts/456'
    
    def test_nested_template_expressions(self):
        """Test nested template expressions."""
        yaml_rules = """
rules:
  - id: nested_template_test
    priority: 100
    condition: "x > 0 and y > 0"
    actions:
      nested_calc: "{{ x + (y * 2) }}"
      complex_nested: "{{ (x + y) * (x - y) }}"
      conditional_nested: "{{ 'high' if (x + y) > 10 else 'low' }}"
      function_nested: "{{ abs(x - y) }}"
      multi_operation: "{{ x * y + x / y }}"
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(x=8, y=3))
        
        # Nested expressions should be evaluated
        assert result.verdict['nested_calc'] == 14        # 8 + (3 * 2) = 8 + 6 = 14
        assert result.verdict['complex_nested'] == 55     # (8 + 3) * (8 - 3) = 11 * 5 = 55
        assert result.verdict['conditional_nested'] == 'high'  # (8 + 3) > 10 = True
        assert result.verdict['function_nested'] == 5     # abs(8 - 3) = 5
        assert result.verdict['multi_operation'] == pytest.approx(26.67, rel=1e-2)  # 8*3 + 8/3 = 24 + 2.67 