"""
Unit Tests for Simplified Engine
================================

Tests for Engine class, YAML parsing, and rule loading in the simplified architecture.
"""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any
import json

from symbolica import Engine, facts
from symbolica.core import ValidationError, SymbolicaError
from symbolica.core.models import Rule, Facts


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


class TestBasicEngine:
    """Basic engine functionality tests."""

    def test_engine_creation(self):
        """Test basic engine creation."""
        rules = [
            Rule(
                id="test_rule",
                priority=1,
                condition="amount > 100",
                actions={"status": "approved"}
            )
        ]
        engine = Engine(rules)
        assert engine.rule_count == 1
        assert engine.get_rule("test_rule").id == "test_rule"

    def test_simple_reasoning(self):
        """Test basic reasoning functionality."""
        rules = [
            Rule(
                id="basic_rule",
                priority=1,
                condition="value > 10",
                actions={"result": "high"}
            )
        ]
        engine = Engine(rules)
        
        result = engine.reason(facts(value=20))
        assert result.verdict["result"] == "high"
        assert "basic_rule" in result.fired_rules
        assert result.execution_time_ms > 0


class TestTracing:
    """Enhanced tracing functionality tests."""

    def test_detailed_tracing(self):
        """Test detailed execution tracing."""
        rules = [
            Rule(
                id="trace_rule",
                priority=10,
                condition="amount > 100",
                actions={"status": "approved", "tier": "premium"},
                tags=["approval", "premium"]
            )
        ]
        engine = Engine(rules)
        
        result = engine.reason(facts(amount=150))
        
        # Check basic result
        assert result.verdict["status"] == "approved"
        assert result.verdict["tier"] == "premium"
        assert "trace_rule" in result.fired_rules
        
        # Check simple reasoning
        assert "trace_rule" in result.reasoning
        assert result.execution_time_ms > 0

    def test_multiple_rules_tracing(self):
        """Test tracing with multiple rules and dependencies."""
        rules = [
            Rule(
                id="basic_check",
                priority=10,
                condition="amount > 0",
                actions={"valid": True}
            ),
            Rule(
                id="premium_check",
                priority=20,
                condition="amount > 1000 and valid == True",
                actions={"tier": "premium"}
            )
        ]
        engine = Engine(rules)
        
        result = engine.reason(facts(amount=1500))
        
        # Both rules should fire
        assert len(result.fired_rules) == 2
        assert "basic_check" in result.fired_rules
        assert "premium_check" in result.fired_rules
        
        # Check simple reasoning includes both rules
        assert "basic_check" in result.reasoning
        assert "premium_check" in result.reasoning

    def test_non_firing_rule_tracing(self):
        """Test tracing for rules that don't fire."""
        rules = [
            Rule(
                id="high_value",
                priority=10,
                condition="amount > 1000",
                actions={"tier": "premium"}
            ),
            Rule(
                id="low_value",
                priority=5,
                condition="amount <= 100",
                actions={"tier": "basic"}
            )
        ]
        engine = Engine(rules)
        
        result = engine.reason(facts(amount=500))
        
        # No rules should fire
        assert len(result.fired_rules) == 0
        assert result.verdict == {}
        
        # Check that reasoning indicates no rules fired
        assert result.reasoning == "No rules fired"


class TestExplanations:
    """Test simple explanation functionality."""

    def test_basic_reasoning(self):
        """Test basic reasoning output."""
        rules = [
            Rule(
                id="approval_rule",
                priority=10,
                condition="score > 80",
                actions={"approved": True, "reason": "high_score"}
            )
        ]
        engine = Engine(rules)
        
        result = engine.reason(facts(score=85))
        
        # Check simple reasoning string
        assert isinstance(result.reasoning, str)
        assert "approval_rule" in result.reasoning
        assert result.reasoning != "No rules fired"

    def test_llm_context_generation(self):
        """Test LLM-friendly context generation."""
        rules = [
            Rule(
                id="customer_tier",
                priority=10,
                condition="purchase_amount > 1000",
                actions={"tier": "premium", "discount": 0.1},
                tags=["classification"]
            )
        ]
        engine = Engine(rules)
        
        result = engine.reason(facts(purchase_amount=1500))
        
        llm_context = result.get_llm_context()
        
        # Check basic structure
        assert "rules_fired" in llm_context
        assert "final_facts" in llm_context
        assert "execution_time_ms" in llm_context
        assert "reasoning" in llm_context

    def test_reasoning_json_output(self):
        """Test JSON output for LLM prompts."""
        rules = [
            Rule(
                id="json_rule",
                priority=10,
                condition="amount > 100",
                actions={"status": "approved"}
            )
        ]
        engine = Engine(rules)
        
        result = engine.reason(facts(amount=150))
        
        json_output = result.get_reasoning_json()
        
        # Should be valid JSON
        parsed = json.loads(json_output)
        assert isinstance(parsed, dict)
        assert "rules_fired" in parsed
        assert "final_facts" in parsed


class TestErrorHandling:
    """Test basic error handling."""

    def test_error_in_condition_handling(self):
        """Test handling when condition evaluation errors."""
        rules = [
            Rule(
                id="error_rule",
                priority=10,
                condition="nonexistent_field > 100",
                actions={"status": "error"}
            )
        ]
        engine = Engine(rules)
        
        result = engine.reason(facts(amount=150))
        
        # Rule should not fire due to error
        assert len(result.fired_rules) == 0
        assert result.verdict == {}


class TestPerformance:
    """Test performance with detailed tracing."""

    def test_tracing_performance(self):
        """Test that detailed tracing doesn't significantly impact performance."""
        rules = [
            Rule(
                id=f"rule_{i}",
                priority=i,
                condition=f"value > {i * 10}",
                actions={"result": f"level_{i}"}
            )
            for i in range(1, 11)  # 10 rules
        ]
        
        engine = Engine(rules)
        
        result = engine.reason(facts(value=55))
        
        # Should complete in reasonable time
        assert result.execution_time_ms < 100  # Less than 100ms
        
        # Should have fired appropriate rules (1-5)
        assert len(result.fired_rules) == 5
        
        # Should have simple reasoning
        assert result.reasoning != "No rules fired"


class TestYAMLParsing:
    """Test YAML parsing with enhanced functionality."""

    def test_yaml_with_tags(self):
        """Test YAML parsing with tags."""
        yaml_content = """
        rules:
          - id: tagged_rule
            priority: 10
            condition: amount > 100
            actions:
              status: approved
            tags: [approval, high-value]
        """
        
        engine = Engine.from_yaml(yaml_content)
        result = engine.reason(facts(amount=150))
        
        # Check that rule fired
        assert "tagged_rule" in result.fired_rules
        assert result.verdict["status"] == "approved"

    def test_yaml_error_handling(self):
        """Test YAML error handling."""
        invalid_yaml = """
        rules:
          - id: invalid_rule
            # Missing condition
            actions:
              status: error
        """
        
        with pytest.raises(Exception):  # Should raise ValidationError
            Engine.from_yaml(invalid_yaml) 