"""
Unit Tests for Engine File Operations
=====================================

Tests for file loading, directory operations, error handling, and performance.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch
from symbolica import Engine, facts
from symbolica.core import ValidationError
from symbolica.core.models import Rule


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

    @pytest.mark.unit
    def test_permission_errors(self):
        """Test handling of permission errors when reading files."""
        with patch('pathlib.Path.read_text') as mock_read:
            mock_read.side_effect = PermissionError("Permission denied")
            
            with pytest.raises(ValidationError):
                Engine.from_file("test.yaml")

    @pytest.mark.unit
    def test_corrupted_file_handling(self, temp_directory):
        """Test handling of corrupted or malformed files."""
        corrupted_file = temp_directory / "corrupted.yaml"
        corrupted_file.write_text("{ invalid yaml content [unclosed")
        
        with pytest.raises(ValidationError):
            Engine.from_file(corrupted_file)


class TestErrorHandling:
    """Test error handling in various scenarios."""
    
    @pytest.mark.unit
    def test_error_in_condition_handling(self):
        """Test graceful handling of errors in rule conditions."""
        error_rules = [
            Rule(
                id="error_rule",
                priority=1,
                condition="nonexistent_function(value)",  # Should cause error
                actions={"result": "error"}
            ),
            Rule(
                id="safe_rule",
                priority=2,
                condition="value > 0",  # Safe condition
                actions={"result": "safe"}
            )
        ]
        
        engine = Engine(error_rules)
        result = engine.reason(facts(value=10))
        
        # Error rule should not fire, safe rule should
        assert "error_rule" not in result.fired_rules
        assert "safe_rule" in result.fired_rules
        assert result.verdict["result"] == "safe"

    @pytest.mark.unit
    def test_engine_resilience(self):
        """Test that engine continues functioning despite individual rule errors."""
        mixed_rules = [
            Rule(id="error1", priority=1, condition="1/0 > 0", actions={"error": True}),
            Rule(id="good1", priority=2, condition="amount > 100", actions={"tier": "bronze"}),
            Rule(id="error2", priority=3, condition="undefined_var == 'test'", actions={"error2": True}),
            Rule(id="good2", priority=4, condition="status == 'active'", actions={"processed": True})
        ]
        
        engine = Engine(mixed_rules)
        result = engine.reason(facts(amount=150, status='active'))
        
        # Good rules should fire, error rules should not
        assert "error1" not in result.fired_rules
        assert "error2" not in result.fired_rules
        assert "good1" in result.fired_rules
        assert "good2" in result.fired_rules
        
        assert result.verdict["tier"] == "bronze"
        assert result.verdict["processed"] is True

    @pytest.mark.unit
    def test_empty_engine_handling(self):
        """Test handling of empty engine (no rules)."""
        engine = Engine()
        result = engine.reason(facts(amount=100))
        
        assert len(result.fired_rules) == 0
        assert len(result.verdict) == 0
        assert result.execution_time_ms >= 0


class TestPerformance:
    """Test performance characteristics."""
    
    @pytest.mark.unit
    def test_tracing_performance(self):
        """Test that tracing doesn't significantly impact performance."""
        # Create a set of rules for performance testing
        rules = []
        for i in range(10):  # Smaller set for unit tests
            rules.append(Rule(
                id=f"rule_{i}",
                priority=i,
                condition=f"value > {i * 10}",
                actions={"result": f"tier_{i}"}
            ))
        
        engine = Engine(rules)
        
        # Test with tracing enabled (default)
        result = engine.reason(facts(value=50))
        
        # Should complete quickly and provide tracing info
        assert result.execution_time_ms < 100  # Should be very fast for 10 rules
        assert len(result.fired_rules) > 0
        assert result.reasoning  # Tracing should be available

    @pytest.mark.unit 
    def test_large_rule_set_handling(self):
        """Test handling of moderately large rule sets."""
        # Create 50 rules for testing
        rules = []
        for i in range(50):
            rules.append(Rule(
                id=f"performance_rule_{i}",
                priority=i,
                condition=f"score >= {i}",
                actions={"level": i, "category": f"tier_{i//10}"}
            ))
        
        engine = Engine(rules)
        result = engine.reason(facts(score=25))
        
        # Should handle 50 rules efficiently
        assert result.execution_time_ms < 200
        assert len(result.fired_rules) > 0
        
        # Verify correct rules fired (score >= 25 means rules 0-25 should fire)
        fired_rule_numbers = [int(rule_id.split('_')[-1]) for rule_id in result.fired_rules]
        assert all(num <= 25 for num in fired_rule_numbers)

    @pytest.mark.unit
    def test_complex_condition_performance(self):
        """Test performance with complex conditions."""
        complex_rules = [
            Rule(
                id="complex_rule_1",
                priority=1,
                condition="amount > 1000 and status == 'active' and risk_score < 50 and country in ['US', 'CA']",
                actions={"complex_result": "approved"}
            ),
            Rule(
                id="complex_rule_2", 
                priority=2,
                condition="(amount * risk_multiplier) > threshold and len(tags) >= min_tags",
                actions={"complex_calc": "computed"}
            )
        ]
        
        engine = Engine(complex_rules)
        
        test_facts = facts(
            amount=1500,
            status='active',
            risk_score=30,
            country='US',
            risk_multiplier=0.8,
            threshold=1000,
            tags=['premium', 'verified', 'loyalty'],
            min_tags=2
        )
        
        result = engine.reason(test_facts)
        
        # Should handle complex conditions efficiently
        assert result.execution_time_ms < 50
        assert "complex_rule_1" in result.fired_rules
        assert result.verdict["complex_result"] == "approved" 