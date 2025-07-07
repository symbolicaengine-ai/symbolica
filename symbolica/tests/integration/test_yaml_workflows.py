"""
YAML Workflow Integration Tests
==============================

Tests for YAML parsing, compilation, and validation workflows.
"""

import pytest
from pathlib import Path

from symbolica import from_yaml
from symbolica.compilation import compile_rules, parse_yaml_file, validate_rules
from symbolica.core import ValidationError, CompilationError


class TestYAMLParsing:
    """Test YAML parsing workflows."""
    
    @pytest.mark.integration
    def test_single_file_parsing(self, yaml_files_directory):
        """Test parsing single YAML file."""
        yaml_file = yaml_files_directory / "main_rules.yaml"
        
        # Parse using compilation module
        result = parse_yaml_file(yaml_file)
        assert result.success is True
        assert len(result.rules) >= 3
        assert len(result.errors) == 0
    
    @pytest.mark.integration
    def test_directory_parsing(self, yaml_files_directory):
        """Test parsing entire directory of YAML files."""
        compiled_result = compile_rules(yaml_files_directory)
        assert compiled_result.success is True
        assert len(compiled_result.rule_set.rules) >= 4  # From multiple files
    
    @pytest.mark.integration
    def test_validation_workflow(self, sample_yaml_rules):
        """Test YAML validation workflow."""
        validation_result = validate_rules(sample_yaml_rules)
        assert validation_result['valid'] is True
        assert len(validation_result['errors']) == 0


class TestAdvancedYAMLFeatures:
    """Test advanced YAML features."""
    
    @pytest.mark.integration
    def test_complex_nested_conditions(self, nested_conditions_yaml):
        """Test complex nested condition parsing."""
        engine = from_yaml(nested_conditions_yaml)
        
        # Verify rules were parsed correctly
        rule_set = engine._rule_set
        assert len(rule_set.rules) == 2
        
        # Find the complex_approval rule
        complex_rule = rule_set.get_rule('complex_approval')
        assert complex_rule is not None
        assert complex_rule.condition.type == "structured"
    
    @pytest.mark.integration
    def test_priority_ordering(self):
        """Test that rules are ordered by priority."""
        yaml_with_priorities = """
rules:
  - id: low_priority
    priority: 10
    if: "amount > 0"
    then:
      set:
        order: third
        
  - id: high_priority
    priority: 100
    if: "amount > 0"
    then:
      set:
        order: first
        
  - id: medium_priority
    priority: 50
    if: "amount > 0"
    then:
      set:
        order: second
"""
        
        engine = from_yaml(yaml_with_priorities)
        
        # Rules should be ordered by priority (highest first)
        rules = list(engine._rule_set.rules)
        priorities = [rule.priority.value for rule in rules]
        assert priorities == [100, 50, 10]  # Sorted highest to lowest 