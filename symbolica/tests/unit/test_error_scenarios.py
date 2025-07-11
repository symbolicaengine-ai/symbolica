"""
Unit Tests for Error Scenarios
==============================

Focused tests for critical error handling and graceful degradation.
"""

import pytest
from unittest.mock import Mock, patch
from symbolica import Engine, facts
from symbolica.core.exceptions import ValidationError, EvaluationError


class TestRuleValidationErrors:
    """Test critical rule validation error scenarios."""
    
    @pytest.mark.unit
    @pytest.mark.critical
    def test_invalid_rule_structure(self):
        """Test various invalid rule structures."""
        invalid_rules = [
            # Missing required fields
            """
rules:
  - priority: 100
    condition: "value > 0"
    actions:
      result: invalid
""",
            # Invalid priority type
            """
rules:
  - id: invalid_priority
    priority: "high"
    condition: "value > 0"
    actions:
      result: invalid
""",
            # Empty condition
            """
rules:
  - id: empty_condition
    priority: 100
    condition: ""
    actions:
      result: invalid
""",
            # Empty actions
            """
rules:
  - id: empty_actions
    priority: 100
    condition: "value > 0"
    actions: {}
""",
        ]
        
        for invalid_rule in invalid_rules:
            with pytest.raises(ValidationError):
                Engine.from_yaml(invalid_rule)
    
    @pytest.mark.unit
    @pytest.mark.critical
    def test_duplicate_rule_ids(self):
        """Test duplicate rule ID detection."""
        duplicate_yaml = """
rules:
  - id: duplicate_rule
    priority: 100
    condition: "value > 0"
    actions:
      result: first
      
  - id: duplicate_rule
    priority: 90
    condition: "value > 10"
    actions:
      result: second
"""
        
        with pytest.raises(ValidationError, match="Duplicate rule ID"):
            Engine.from_yaml(duplicate_yaml)
    
    @pytest.mark.unit
    @pytest.mark.extended
    def test_invalid_yaml_syntax(self):
        """Test handling of invalid YAML syntax."""
        invalid_yaml_samples = [
            # Unclosed list
            """
rules:
  - id: unclosed_list
    priority: 100
    condition: "value > 0"
    actions:
      result: [unclosed
""",
            # Invalid indentation
            """
rules:
- id: bad_indent
  priority: 100
   condition: "value > 0"
    actions:
      result: bad
""",
        ]
        
        for invalid_yaml in invalid_yaml_samples:
            with pytest.raises(ValidationError):
                Engine.from_yaml(invalid_yaml)


class TestConditionEvaluationErrors:
    """Test condition evaluation error scenarios."""
    
    @pytest.mark.unit
    @pytest.mark.extended
    def test_syntax_errors_in_conditions(self):
        """Test handling of syntax errors in conditions."""
        syntax_error_rules = [
            # Unmatched parentheses
            """
rules:
  - id: unmatched_parens
    priority: 100
    condition: "value > 0 and (status == 'active'"
    actions:
      result: syntax_error
""",
            # Invalid operators
            """
rules:
  - id: invalid_operators
    priority: 100
    condition: "value >> 10"
    actions:
      result: syntax_error
""",
        ]
        
        for syntax_error_rule in syntax_error_rules:
            with pytest.raises((ValidationError, EvaluationError)):
                engine = Engine.from_yaml(syntax_error_rule)
                engine.reason(facts(value=10, status='active'))
    
    @pytest.mark.unit
    @pytest.mark.critical
    def test_runtime_evaluation_errors(self):
        """Test runtime evaluation errors with graceful fallback."""
        runtime_error_yaml = """
rules:
  - id: division_by_zero
    priority: 100
    condition: "value / zero_field > 1"
    actions:
      result: division_error
      
  - id: missing_field_access
    priority: 90
    condition: "nonexistent_field > 10"
    actions:
      result: missing_field
      
  - id: type_error
    priority: 80
    condition: "string_field + numeric_field > 10"
    actions:
      result: type_error
      
  - id: fallback_rule
    priority: 70
    condition: "True"
    actions:
      fallback: true
"""
        
        engine = Engine.from_yaml(runtime_error_yaml)
        result = engine.reason(facts(
            value=10,
            zero_field=0,
            string_field='hello',
            numeric_field=5
        ))
        
        # Error rules should not fire, fallback should work
        assert 'division_by_zero' not in result.fired_rules
        assert 'missing_field_access' not in result.fired_rules
        assert 'type_error' not in result.fired_rules
        assert 'fallback_rule' in result.fired_rules
        assert result.verdict['fallback'] is True


class TestActionEvaluationErrors:
    """Test action evaluation error scenarios."""
    
    @pytest.mark.unit
    @pytest.mark.critical
    def test_action_expression_errors(self):
        """Test errors in action expressions with fallback behavior."""
        action_error_yaml = """
rules:
  - id: action_error_test
    priority: 100
    condition: "value > 0"
    actions:
      invalid_calc: "{{ value / zero_field }}"
      missing_field_calc: "{{ nonexistent_field * 2 }}"
      valid_calc: "{{ value * 2 }}"
      string_literal: CALCULATED
"""
        
        engine = Engine.from_yaml(action_error_yaml)
        result = engine.reason(facts(value=10, zero_field=0))
        
        # Invalid calculations should fallback to original strings
        assert result.verdict['invalid_calc'] == 'value / zero_field'
        assert result.verdict['missing_field_calc'] == 'nonexistent_field * 2'
        
        # Valid calculations should work
        assert result.verdict['valid_calc'] == 20
        assert result.verdict['string_literal'] == 'CALCULATED'


class TestLLMIntegrationErrors:
    """Test LLM integration error scenarios."""
    
    @pytest.mark.unit
    @pytest.mark.extended
    def test_llm_client_errors(self):
        """Test various LLM client errors with graceful fallback."""
        error_types = [
            ConnectionError("Network error"),
            TimeoutError("Request timeout"),
            ValueError("Invalid response"),
        ]
        
        for error in error_types:
            mock_client = Mock()
            mock_client.complete.side_effect = error
            
            error_yaml = """
rules:
  - id: llm_error_test
    priority: 100
    condition: "PROMPT('Test prompt') == 'success'"
    actions:
      should_not_trigger: true
      
  - id: fallback_rule
    priority: 90
    condition: "True"
    actions:
      fallback: true
      error_handled: true
"""
            
            engine = Engine.from_yaml(error_yaml, llm_client=mock_client)
            result = engine.reason(facts(value=1))
            
            # LLM rule should fail, fallback should work
            assert 'llm_error_test' not in result.fired_rules
            assert 'fallback_rule' in result.fired_rules
            assert result.verdict['fallback'] is True
            assert result.verdict['error_handled'] is True
    
    @pytest.mark.unit
    @pytest.mark.extended
    def test_llm_invalid_responses(self):
        """Test handling of invalid LLM responses."""
        invalid_responses = [
            None,  # None response
            '',    # Empty response
            'not_a_number',  # Invalid type conversion
        ]
        
        for invalid_response in invalid_responses:
            mock_client = Mock()
            mock_client.complete.return_value = Mock(content=invalid_response)
            
            invalid_response_yaml = """
rules:
  - id: invalid_response_test
    priority: 100
    condition: "PROMPT('Rate 1-10: {item}', 'int') > 5"
    actions:
      should_not_trigger: true
      
  - id: response_fallback
    priority: 90
    condition: "True"
    actions:
      fallback: invalid_response_handled
"""
            
            engine = Engine.from_yaml(invalid_response_yaml, llm_client=mock_client)
            result = engine.reason(facts(item='test'))
            
            # Invalid response rule should fail, fallback should work
            assert 'invalid_response_test' not in result.fired_rules
            assert 'response_fallback' in result.fired_rules
            assert result.verdict['fallback'] == 'invalid_response_handled'


class TestFileAndYAMLErrors:
    """Test file and YAML loading error scenarios."""
    
    @pytest.mark.unit
    @pytest.mark.critical
    def test_file_not_found_errors(self):
        """Test file not found errors."""
        with pytest.raises(ValidationError, match="File not found"):
            Engine.from_file("nonexistent_file.yaml")
    
    @pytest.mark.unit
    @pytest.mark.critical
    def test_directory_not_found_errors(self):
        """Test directory not found errors."""
        with pytest.raises(ValidationError, match="Directory not found"):
            Engine.from_directory("nonexistent_directory")
    
    @pytest.mark.unit
    @pytest.mark.extended
    def test_corrupted_yaml_files(self):
        """Test handling of corrupted YAML files."""
        corrupted_yaml_samples = [
            "{ invalid yaml content",
            "rules:\n  - invalid: [unclosed",
        ]
        
        for corrupted_yaml in corrupted_yaml_samples:
            with pytest.raises(ValidationError):
                Engine.from_yaml(corrupted_yaml)


class TestErrorIsolation:
    """Test that errors in one rule don't affect others."""
    
    @pytest.mark.unit
    @pytest.mark.critical
    def test_error_isolation(self):
        """Test that errors in one rule don't affect others."""
        isolation_yaml = """
rules:
  - id: error_rule_1
    priority: 100
    condition: "value / zero_field > 0"
    actions:
      result: error_1
      
  - id: error_rule_2
    priority: 90
    condition: "nonexistent_function() == True"
    actions:
      result: error_2
      
  - id: working_rule_1
    priority: 80
    condition: "value > 5"
    actions:
      result: working_1
      
  - id: working_rule_2
    priority: 70
    condition: "status == 'active'"
    actions:
      result: working_2
"""
        
        engine = Engine.from_yaml(isolation_yaml)
        result = engine.reason(facts(
            value=10,
            zero_field=0,
            status='active'
        ))
        
        # Error rules should fail, working rules should succeed
        assert 'error_rule_1' not in result.fired_rules
        assert 'error_rule_2' not in result.fired_rules
        assert 'working_rule_1' in result.fired_rules
        assert 'working_rule_2' in result.fired_rules
        
        # Should have results from working rules
        assert result.verdict['result'] == 'working_2'  # Last rule to fire
    
    @pytest.mark.unit
    @pytest.mark.extended
    def test_empty_facts_handling(self):
        """Test handling of empty facts."""
        empty_facts_yaml = """
rules:
  - id: empty_facts_test
    priority: 100
    condition: "True"
    actions:
      result: empty_facts_handled
      
  - id: fact_dependent_test
    priority: 90
    condition: "value > 0"
    actions:
      result: should_not_trigger
"""
        
        engine = Engine.from_yaml(empty_facts_yaml)
        result = engine.reason(facts())
        
        # Only rule with True condition should fire
        assert 'empty_facts_test' in result.fired_rules
        assert 'fact_dependent_test' not in result.fired_rules
        assert result.verdict['result'] == 'empty_facts_handled' 