"""
Unit Tests for Engine YAML Functionality
========================================

Tests for YAML parsing, validation, and structured condition handling.
"""

import pytest
from symbolica import Engine
from symbolica.core import ValidationError


class TestYamlParsing:
    """Test YAML parsing functionality."""
    
    @pytest.mark.unit
    def test_simple_yaml_parsing(self):
        """Test parsing simple YAML rules."""
        simple_yaml = """
rules:
  - id: simple_rule
    priority: 100
    if: "amount > 1000"
    then:
      tier: premium
      approved: true
    tags: [simple, test]
"""
        
        engine = Engine.from_yaml(simple_yaml)
        analysis = engine.get_analysis()
        
        assert analysis['rule_count'] == 1
        assert analysis['rule_ids'] == ['simple_rule']
    
    @pytest.mark.unit
    def test_structured_condition_parsing(self, structured_conditions_yaml):
        """Test parsing structured conditions (all, any, not)."""
        engine = Engine.from_yaml(structured_conditions_yaml)
        
        analysis = engine.get_analysis()
        assert analysis['rule_count'] == 3
        assert 'complex_approval' in analysis['rule_ids']
        assert 'fraud_detection' in analysis['rule_ids']
        assert 'nested_logic' in analysis['rule_ids']
    
    @pytest.mark.unit
    def test_nested_set_format(self):
        """Test parsing rules with nested 'set' format."""
        nested_yaml = """
rules:
  - id: nested_rule
    priority: 100
    if: "amount > 1000"
    then:
      set:
        tier: premium
        discount: 0.15
"""
        
        engine = Engine.from_yaml(nested_yaml)
        analysis = engine.get_analysis()
        
        assert analysis['rule_count'] == 1
    
    @pytest.mark.unit
    def test_alternative_field_names(self):
        """Test parsing with alternative field names (condition/if, actions/then)."""
        alt_yaml = """
rules:
  - id: alt_rule
    priority: 100
    condition: "amount > 1000"
    actions:
      tier: premium
"""
        
        engine = Engine.from_yaml(alt_yaml)
        analysis = engine.get_analysis()
        
        assert analysis['rule_count'] == 1
    
    @pytest.mark.unit
    def test_tags_parsing(self):
        """Test that tags are properly parsed."""
        tagged_yaml = """
rules:
  - id: tagged_rule
    priority: 100
    if: "amount > 1000"
    then:
      tier: premium
    tags: [customer, premium, test]
"""
        
        engine = Engine.from_yaml(tagged_yaml)
        analysis = engine.get_analysis()
        assert analysis['rule_count'] == 1

    @pytest.mark.unit
    def test_yaml_with_tags(self):
        """Test YAML parsing with tags."""
        yaml_with_tags = """
rules:
  - id: customer_rule
    priority: 100
    if: "customer_type == 'premium'"
    then:
      discount: 0.15
      priority_support: true
    tags: [customer, premium, discount]
    
  - id: risk_rule
    priority: 90
    if: "risk_score > 70"
    then:
      requires_review: true
      alert_level: high
    tags: [risk, security, review]
"""
        
        engine = Engine.from_yaml(yaml_with_tags)
        analysis = engine.get_analysis()
        
        assert analysis['rule_count'] == 2
        assert 'customer_rule' in analysis['rule_ids']
        assert 'risk_rule' in analysis['rule_ids']


class TestYamlValidation:
    """Test YAML validation and error handling."""
    
    @pytest.mark.unit
    def test_invalid_yaml_syntax(self):
        """Test handling of invalid YAML syntax."""
        invalid_yaml = """
rules:
  - id: broken
    if: amount > 1000
    then:
      tier: premium
      invalid: [unclosed
"""
        
        with pytest.raises(ValidationError, match="Invalid YAML"):
            Engine.from_yaml(invalid_yaml)
    
    @pytest.mark.unit
    def test_missing_rules_key(self):
        """Test error when 'rules' key is missing."""
        no_rules_yaml = """
other_key: some_value
data: more_data
"""
        
        with pytest.raises(ValidationError, match="YAML must contain 'rules' key"):
            Engine.from_yaml(no_rules_yaml)
    
    @pytest.mark.unit
    def test_empty_rules(self):
        """Test error when rules list is empty."""
        empty_rules_yaml = """
rules: []
"""
        
        with pytest.raises(ValidationError, match="No valid rules found"):
            Engine.from_yaml(empty_rules_yaml)
    
    @pytest.mark.unit
    def test_missing_required_fields(self):
        """Test validation of required rule fields."""
        # Missing ID
        missing_id_yaml = """
rules:
  - priority: 100
    if: "amount > 1000"
    then:
      tier: premium
"""
        
        with pytest.raises(ValidationError, match="Rule must have 'id' field"):
            Engine.from_yaml(missing_id_yaml)
        
        # Missing condition
        missing_condition_yaml = """
rules:
  - id: test_rule
    priority: 100
    then:
      tier: premium
"""
        
        with pytest.raises(ValidationError, match="Rule must have 'condition' or 'if' field"):
            Engine.from_yaml(missing_condition_yaml)
        
        # Missing actions
        missing_actions_yaml = """
rules:
  - id: test_rule
    priority: 100
    if: "amount > 1000"
"""
        
        with pytest.raises(ValidationError, match="Rule must have 'actions' or 'then' field"):
            Engine.from_yaml(missing_actions_yaml)
    
    @pytest.mark.unit
    def test_duplicate_rule_ids(self):
        """Test error when duplicate rule IDs are found."""
        duplicate_yaml = """
rules:
  - id: duplicate_rule
    priority: 100
    if: "amount > 1000"
    then:
      tier: premium
      
  - id: duplicate_rule
    priority: 90
    if: "amount > 2000"
    then:
      tier: gold
"""
        
        with pytest.raises(ValidationError, match="Duplicate rule ID"):
            Engine.from_yaml(duplicate_yaml)

    @pytest.mark.unit
    def test_yaml_error_handling(self):
        """Test comprehensive YAML error handling."""
        invalid_yamls = [
            # Invalid YAML structure
            """
            rules:
              - id: invalid
                if: amount > 1000
                then: [invalid structure
            """,
            # Missing quotes around string values
            """
            rules:
              - id: quote_test
                priority: 100
                if: status == active  # Missing quotes
                then:
                  result: approved
            """,
        ]
        
        for invalid_yaml in invalid_yamls:
            with pytest.raises(ValidationError):
                Engine.from_yaml(invalid_yaml)


class TestConditionParsing:
    """Test structured condition parsing."""
    
    @pytest.mark.unit
    def test_all_condition_parsing(self):
        """Test parsing 'all' conditions."""
        all_yaml = """
rules:
  - id: all_test
    priority: 100
    if:
      all:
        - "amount > 1000"
        - "status == 'active'"
        - "country == 'US'"
    then:
      approved: true
"""
        
        engine = Engine.from_yaml(all_yaml)
        analysis = engine.get_analysis()
        assert analysis['rule_count'] == 1
    
    @pytest.mark.unit
    def test_any_condition_parsing(self):
        """Test parsing 'any' conditions."""
        any_yaml = """
rules:
  - id: any_test
    priority: 100
    if:
      any:
        - "amount > 5000"
        - "user_type == 'vip'"
        - "risk_score < 20"
    then:
      special_treatment: true
"""
        
        engine = Engine.from_yaml(any_yaml)
        analysis = engine.get_analysis()
        assert analysis['rule_count'] == 1
    
    @pytest.mark.unit
    def test_not_condition_parsing(self):
        """Test parsing 'not' conditions."""
        not_yaml = """
rules:
  - id: not_test
    priority: 100
    if:
      not: "status == 'inactive'"
    then:
      process: true
"""
        
        engine = Engine.from_yaml(not_yaml)
        analysis = engine.get_analysis()
        assert analysis['rule_count'] == 1
    
    @pytest.mark.unit
    def test_nested_conditions(self):
        """Test parsing deeply nested conditions."""
        nested_yaml = """
rules:
  - id: nested_test
    priority: 100
    if:
      all:
        - "amount > 1000"
        - any:
          - "user_type == 'premium'"
          - all:
            - "account_balance > 10000"
            - "years_active >= 5"
    then:
      complex_approval: true
"""
        
        engine = Engine.from_yaml(nested_yaml)
        analysis = engine.get_analysis()
        assert analysis['rule_count'] == 1
    
    @pytest.mark.unit
    def test_invalid_structured_conditions(self):
        """Test validation of invalid structured conditions."""
        # Invalid: 'all' must contain a list
        invalid_all_yaml = """
rules:
  - id: invalid_all
    priority: 100
    if:
      all: "not a list"
    then:
      result: true
"""
        
        with pytest.raises(ValidationError, match="'all' must contain a non-empty list of conditions"):
            Engine.from_yaml(invalid_all_yaml)
        
        # Invalid: unknown structured condition key
        invalid_key_yaml = """
rules:
  - id: invalid_key
    priority: 100
    if:
      unknown_key: ["condition1"]
    then:
      result: true
"""
        
        with pytest.raises(ValidationError, match="Unknown structured condition key"):
            Engine.from_yaml(invalid_key_yaml) 