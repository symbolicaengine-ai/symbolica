"""
Unit Tests for Compilation Pipeline
===================================

Tests for YAML parsing, rule compilation, optimization, and validation.
"""

import pytest
from pathlib import Path

from symbolica.compilation import (
    RuleParser, RuleCompiler, parse_yaml_string, compile_rules
)
from symbolica.core import ValidationError, CompilationError


class TestRuleParser:
    """Test the YAML rule parser."""
    
    @pytest.mark.unit
    def test_parse_simple_rule(self):
        """Test parsing a simple rule."""
        yaml_content = """
rules:
  - id: simple_test
    priority: 100
    if: "amount > 1000"
    then:
      set:
        tier: premium
"""
        
        result = parse_yaml_string(yaml_content)
        assert result.success is True
        assert len(result.rules) == 1
        
        rule = result.rules[0]
        assert rule['id'] == 'simple_test'
        assert rule['priority'] == 100
        assert rule['if'] == 'amount > 1000'
    
    @pytest.mark.unit
    def test_parse_structured_conditions(self):
        """Test parsing structured conditions."""
        yaml_content = """
rules:
  - id: structured_test
    priority: 100
    if:
      all:
        - "amount > 1000"
        - "status == 'active'"
    then:
      set:
        approved: true
"""
        
        result = parse_yaml_string(yaml_content)
        assert result.success is True
        
        rule = result.rules[0]
        condition = rule['if']
        assert isinstance(condition, dict)
        assert 'all' in condition
        assert len(condition['all']) == 2
    
    @pytest.mark.unit
    def test_parse_invalid_yaml(self):
        """Test parsing invalid YAML."""
        invalid_yaml = """
rules:
  - id: broken
    if: amount > 1000
    then:
      set:
        tier: premium
        invalid: [unclosed
"""
        
        result = parse_yaml_string(invalid_yaml)
        assert result.success is False
        assert len(result.errors) > 0


class TestRuleCompiler:
    """Test the rule compiler."""
    
    @pytest.mark.unit
    def test_compile_simple_rules(self, sample_yaml_rules):
        """Test compiling simple rules."""
        result = compile_rules(sample_yaml_rules)
        
        assert result.success is True
        assert result.rule_set is not None
        assert len(result.rule_set.rules) >= 3
        assert len(result.errors) == 0
    
    @pytest.mark.unit
    def test_compile_with_validation_errors(self):
        """Test compilation with validation errors."""
        invalid_rules = """
rules:
  - id: ""  # Invalid empty ID
    priority: 100
    if: "amount > 1000"
    then:
      set:
        tier: premium
"""
        
        result = compile_rules(invalid_rules)
        assert result.success is False
        assert len(result.errors) > 0
    
    @pytest.mark.unit
    def test_compilation_stats(self, sample_yaml_rules):
        """Test that compilation provides statistics."""
        result = compile_rules(sample_yaml_rules)
        
        assert 'compilation_time_ms' in result.stats
        assert 'rules_compiled' in result.stats
        assert result.stats['rules_compiled'] >= 3 