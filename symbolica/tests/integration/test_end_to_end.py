"""
End-to-End Integration Tests
===========================

Complete workflow tests from YAML rule definition to execution results.
"""

import pytest
from typing import Dict, Any

from symbolica import Engine, from_yaml, quick_reason
from symbolica.core import TraceLevel, ExecutionError


class TestBasicWorkflows:
    """Test basic end-to-end workflows."""
    
    @pytest.mark.integration
    def test_simple_yaml_to_execution(self, sample_yaml_rules, sample_facts):
        """Test complete workflow: YAML → Engine → Execution."""
        # Create engine from YAML
        engine = from_yaml(sample_yaml_rules)
        
        # Execute reasoning
        result = engine.reason(sample_facts)
        
        # Verify results
        assert result.success is True
        assert len(result.fired_rules) > 0
        assert 'tier' in result.verdict
        assert result.verdict['tier'] == 'premium'
        assert result.execution_time_ms > 0
    
    @pytest.mark.integration
    def test_nested_conditions_workflow(self, nested_conditions_yaml):
        """Test complex nested conditions workflow."""
        engine = from_yaml(nested_conditions_yaml)
        
        # Test case 1: Should trigger complex_approval via high amount + active
        facts1 = {
            'amount': 1500,
            'status': 'active',
            'user_type': 'standard',
            'account_balance': 2000,
            'risk_score': 30,
            'country': 'US',
            'age': 30
        }
        
        result1 = engine.reason(facts1)
        assert result1.success is True
        assert 'complex_approval' in result1.fired_rules
        assert result1.verdict['approved'] is True
        assert result1.verdict['approval_reason'] == 'high_value_or_premium'
        
        # Test case 2: Should trigger complex_approval via premium + high balance
        facts2 = {
            'amount': 500,
            'status': 'pending',
            'user_type': 'premium',
            'account_balance': 15000,
            'risk_score': 20,
            'country': 'US',
            'age': 35
        }
        
        result2 = engine.reason(facts2)
        assert result2.success is True
        assert 'complex_approval' in result2.fired_rules
        assert result2.verdict['approved'] is True
        
        # Test case 3: Should trigger fraud_detection
        facts3 = {
            'amount': 6000,
            'status': 'active',
            'user_type': 'standard',
            'account_balance': 2000,
            'risk_score': 85,
            'country': 'XX',
            'age': 19
        }
        
        result3 = engine.reason(facts3)
        assert result3.success is True
        assert 'fraud_detection' in result3.fired_rules
        assert result3.verdict['flagged'] is True
        assert result3.verdict['review_required'] is True
    
    @pytest.mark.integration
    def test_quick_reason_function(self, sample_yaml_rules):
        """Test the quick_reason convenience function."""
        facts = {
            'amount': 2000,
            'status': 'active',
            'user_type': 'premium',
            'account_balance': 6000
        }
        
        # Quick reasoning
        result = quick_reason(sample_yaml_rules, facts)
        
        assert result.success is True
        assert len(result.fired_rules) >= 2  # Should fire multiple rules
        assert 'tier' in result.verdict
        assert result.verdict['approved'] is True
    
    @pytest.mark.integration
    def test_multiple_rule_interactions(self, sample_yaml_rules):
        """Test interactions between multiple rules."""
        engine = from_yaml(sample_yaml_rules)
        
        # Facts that should trigger multiple rules
        facts = {
            'amount': 1500,
            'status': 'active',
            'user_type': 'premium',
            'account_balance': 6000,
            'risk_score': 30,
            'country': 'US'
        }
        
        result = engine.reason(facts)
        
        # Should fire multiple rules
        assert len(result.fired_rules) >= 2
        
        # Check combined verdict
        verdict = result.verdict
        assert verdict['tier'] == 'premium'  # From high_value_customer
        assert verdict['approved'] is True   # From risk_assessment
        assert verdict['bonus_eligible'] is True  # From account_bonus
        
        # All rules should have executed successfully
        assert result.success is True
        assert len(result.errors) == 0
    
    @pytest.mark.integration
    def test_no_rules_fired(self):
        """Test case where no rules should fire."""
        yaml_rules = """
rules:
  - id: high_amount_only
    priority: 100
    if: "amount > 10000"
    then:
      set:
        tier: vip
"""
        engine = from_yaml(yaml_rules)
        
        # Facts that don't match any rules
        facts = {'amount': 500, 'status': 'pending'}
        
        result = engine.reason(facts)
        
        assert result.success is True
        assert len(result.fired_rules) == 0
        assert result.verdict == {}
        assert result.execution_time_ms > 0


class TestErrorHandling:
    """Test error handling in end-to-end workflows."""
    
    @pytest.mark.integration
    def test_invalid_yaml_handling(self):
        """Test handling of invalid YAML."""
        invalid_yaml = """
rules:
  - id: broken_rule
    if: "amount >"  # Invalid expression
    then:
      set:
        tier: premium
"""
        
        with pytest.raises(ExecutionError):
            from_yaml(invalid_yaml)
    
    @pytest.mark.integration
    def test_runtime_evaluation_errors(self):
        """Test handling of runtime evaluation errors."""
        yaml_rules = """
rules:
  - id: division_by_zero
    priority: 100
    if: "amount / divisor > 100"
    then:
      set:
        result: calculated
"""
        
        engine = from_yaml(yaml_rules)
        
        # Facts that will cause division by zero
        facts = {'amount': 1000, 'divisor': 0}
        
        result = engine.reason(facts)
        
        # Should handle error gracefully
        assert result.success is False
        assert len(result.errors) > 0
        assert 'division' in result.errors[0].lower()
    
    @pytest.mark.integration
    def test_missing_field_handling(self):
        """Test handling of missing fields."""
        yaml_rules = """
rules:
  - id: field_check
    priority: 100
    if: "nonexistent_field > 100"
    then:
      set:
        status: processed
"""
        
        engine = from_yaml(yaml_rules)
        facts = {'amount': 1000}
        
        result = engine.reason(facts)
        
        # Should handle missing field gracefully
        assert result.success is False
        assert len(result.errors) > 0


class TestTracing:
    """Test tracing functionality in workflows."""
    
    @pytest.mark.integration
    def test_basic_tracing(self, sample_yaml_rules):
        """Test basic tracing functionality."""
        engine = from_yaml(sample_yaml_rules)
        
        facts = {
            'amount': 1500,
            'status': 'active',
            'user_type': 'premium',
            'account_balance': 6000,
            'risk_score': 30,
            'country': 'US'
        }
        
        # Execute with tracing
        result = engine.reason(facts, trace_level=TraceLevel.BASIC)
        
        assert result.success is True
        assert hasattr(result, 'trace_data')
        assert result.trace_data is not None
    
    @pytest.mark.integration
    def test_detailed_tracing(self, sample_yaml_rules):
        """Test detailed tracing functionality."""
        engine = from_yaml(sample_yaml_rules)
        
        facts = {
            'amount': 1500,
            'status': 'active',
            'user_type': 'premium',
            'account_balance': 6000
        }
        
        # Execute with detailed tracing
        result = engine.reason(facts, trace_level=TraceLevel.DETAILED)
        
        assert result.success is True
        assert hasattr(result, 'trace_data')
        
        # Detailed tracing should provide more information
        if result.trace_data:
            assert len(result.trace_data) > 0


class TestPerformance:
    """Test performance characteristics of end-to-end workflows."""
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_large_rule_set_performance(self):
        """Test performance with large rule sets."""
        # Generate large rule set
        rules = ["rules:"]
        for i in range(100):
            rules.append(f"""
  - id: rule_{i}
    priority: {100 - i}
    if: "amount > {i * 100} and field_{i % 10} == 'value_{i % 5}'"
    then:
      set:
        result_{i}: true
        priority_{i}: {100 - i}
""")
        
        large_yaml = '\n'.join(rules)
        engine = from_yaml(large_yaml)
        
        # Test facts that might match several rules
        facts = {
            'amount': 5000,
            **{f'field_{i}': f'value_{i % 5}' for i in range(10)}
        }
        
        result = engine.reason(facts)
        
        # Should complete in reasonable time
        assert result.execution_time_ms < 1000  # Less than 1 second
        assert result.success is True
    
    @pytest.mark.integration
    @pytest.mark.benchmark
    def test_repeated_execution_performance(self, engine_with_rules, performance_facts):
        """Test performance of repeated executions."""
        engine = engine_with_rules
        
        # Execute reasoning on many fact sets
        results = []
        total_time = 0
        
        for fact_set in performance_facts[:100]:  # Test first 100
            result = engine.reason(fact_set)
            results.append(result)
            total_time += result.execution_time_ms
        
        # Verify all executions succeeded
        successful_results = [r for r in results if r.success]
        assert len(successful_results) == len(results)
        
        # Average execution time should be reasonable
        avg_time = total_time / len(results)
        assert avg_time < 50  # Less than 50ms average
    
    @pytest.mark.integration
    def test_caching_effectiveness(self, sample_yaml_rules):
        """Test that caching improves performance."""
        engine = from_yaml(sample_yaml_rules)
        
        facts = {
            'amount': 1500,
            'status': 'active',
            'user_type': 'premium',
            'account_balance': 6000
        }
        
        # First execution (cold cache)
        result1 = engine.reason(facts)
        time1 = result1.execution_time_ms
        
        # Second execution (warm cache)
        result2 = engine.reason(facts)
        time2 = result2.execution_time_ms
        
        # Results should be identical
        assert result1.verdict == result2.verdict
        assert result1.fired_rules == result2.fired_rules
        
        # Second execution should be faster (or at least not significantly slower)
        assert time2 <= time1 * 1.5  # Allow 50% variance for timing fluctuations 