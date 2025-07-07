"""
Unit Tests for Simplified Engine
================================

Tests for Engine class, YAML parsing, and rule loading in the simplified architecture.
"""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any

from symbolica import Engine
from symbolica.core import ValidationError, SymbolicaError


class TestEngineCreation:
    """Test Engine creation and initialization."""
    
    @pytest.mark.unit
    def test_engine_basic_creation(self):
        """Test basic engine creation."""
        engine = Engine()
        
        assert engine._rules == []
        assert engine._evaluator is not None
        assert engine._executor is not None
        assert engine._dag_strategy is not None
    
    @pytest.mark.unit
    def test_engine_from_yaml_string(self, sample_yaml_rules):
        """Test engine creation from YAML string."""
        engine = Engine.from_yaml(sample_yaml_rules)
        
        analysis = engine.get_analysis()
        assert analysis['rule_count'] == 3
        assert 'high_value_customer' in analysis['rule_ids']
        assert 'risk_assessment' in analysis['rule_ids']
        assert 'account_bonus' in analysis['rule_ids']
    
    @pytest.mark.unit
    def test_engine_from_file(self, temp_directory, sample_yaml_rules):
        """Test engine creation from YAML file."""
        yaml_file = temp_directory / "test_rules.yaml"
        yaml_file.write_text(sample_yaml_rules)
        
        engine = Engine.from_file(yaml_file)
        
        analysis = engine.get_analysis()
        assert analysis['rule_count'] == 3
    
    @pytest.mark.unit
    def test_engine_from_directory(self, yaml_files_directory):
        """Test engine creation from directory with recursive search."""
        engine = Engine.from_directory(yaml_files_directory)
        
        analysis = engine.get_analysis()
        assert analysis['rule_count'] == 4  # 1 general + 2 customer + 1 security
        assert 'general_rule' in analysis['rule_ids']
        assert 'vip_customer' in analysis['rule_ids']
        assert 'loyalty_bonus' in analysis['rule_ids']
        assert 'high_risk_transaction' in analysis['rule_ids']


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
        # Note: We'd need to enhance the engine to expose rule details to fully test this
        analysis = engine.get_analysis()
        assert analysis['rule_count'] == 1


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


class TestFileOperations:
    """Test file loading operations."""
    
    @pytest.mark.unit
    def test_file_not_found(self):
        """Test error when file doesn't exist."""
        with pytest.raises(ValidationError, match="File not found"):
            Engine.from_file("nonexistent_file.yaml")
    
    @pytest.mark.unit
    def test_directory_not_found(self):
        """Test error when directory doesn't exist."""
        with pytest.raises(ValidationError, match="Directory not found"):
            Engine.from_directory("nonexistent_directory")
    
    @pytest.mark.unit
    def test_path_is_not_directory(self, temp_directory):
        """Test error when path is not a directory."""
        file_path = temp_directory / "not_a_directory.txt"
        file_path.write_text("some content")
        
        with pytest.raises(ValidationError, match="Path is not a directory"):
            Engine.from_directory(file_path)
    
    @pytest.mark.unit
    def test_no_yaml_files_in_directory(self, temp_directory):
        """Test error when no YAML files found in directory."""
        # Create directory with non-YAML files
        (temp_directory / "readme.txt").write_text("This is not a YAML file")
        (temp_directory / "config.json").write_text('{"key": "value"}')
        
        with pytest.raises(ValidationError, match="No YAML files found in directory"):
            Engine.from_directory(temp_directory)
    
    @pytest.mark.unit
    def test_duplicate_ids_across_files(self, temp_directory):
        """Test error when duplicate rule IDs exist across multiple files."""
        # First file
        file1_content = """
rules:
  - id: shared_rule
    priority: 100
    if: "amount > 1000"
    then:
      tier: premium
"""
        (temp_directory / "file1.yaml").write_text(file1_content)
        
        # Second file with same rule ID
        file2_content = """
rules:
  - id: shared_rule
    priority: 90
    if: "amount > 2000"
    then:
      tier: gold
"""
        (temp_directory / "file2.yaml").write_text(file2_content)
        
        with pytest.raises(ValidationError, match="Duplicate rule ID"):
            Engine.from_directory(temp_directory)


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
        # Test that it doesn't throw an error and creates the rule
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
        
        with pytest.raises(ValidationError, match="'all' must contain a list"):
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
        
        with pytest.raises(ValidationError, match="Structured condition must contain"):
            Engine.from_yaml(invalid_key_yaml)


class TestEngineAnalysis:
    """Test engine analysis and metadata."""
    
    @pytest.mark.unit
    def test_get_analysis(self, sample_yaml_rules):
        """Test engine analysis functionality."""
        engine = Engine.from_yaml(sample_yaml_rules)
        
        analysis = engine.get_analysis()
        
        assert 'rule_count' in analysis
        assert 'rule_ids' in analysis
        assert 'avg_priority' in analysis
        
        assert analysis['rule_count'] == 3
        assert len(analysis['rule_ids']) == 3
        assert analysis['avg_priority'] > 0
    
    @pytest.mark.unit
    def test_analysis_empty_engine(self):
        """Test analysis of empty engine."""
        engine = Engine()
        
        analysis = engine.get_analysis()
        
        assert analysis['rule_count'] == 0
        assert analysis['rule_ids'] == []
        assert analysis['avg_priority'] == 0 