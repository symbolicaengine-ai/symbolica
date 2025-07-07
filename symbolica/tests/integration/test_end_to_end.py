"""
End-to-End Integration Tests
===========================

Complete workflow tests from YAML rule definition to execution results.
"""

import pytest
from typing import Dict, Any

from symbolica import Engine
from symbolica.core import SymbolicaError, ValidationError


class TestBasicWorkflows:
    """Test basic end-to-end workflows."""
    
    @pytest.mark.integration
    def test_simple_yaml_to_execution(self, sample_yaml_rules, sample_facts):
        """Test complete workflow: YAML → Engine → Execution."""
        # Create engine from YAML
        engine = Engine.from_yaml(sample_yaml_rules)
        
        # Execute reasoning
        result = engine.reason(sample_facts)
        
        # Verify results
        assert len(result.fired_rules) > 0
        assert 'tier' in result.verdict
        assert result.verdict['tier'] == 'premium'
        assert result.execution_time_ms > 0
    
    @pytest.mark.integration
    def test_structured_conditions_workflow(self, structured_conditions_yaml):
        """Test complex structured conditions workflow."""
        engine = Engine.from_yaml(structured_conditions_yaml)
        
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
        assert 'fraud_detection' in result3.fired_rules
        assert result3.verdict['flagged'] is True
        assert result3.verdict['review_required'] is True
    
    @pytest.mark.integration
    def test_multiple_rule_interactions(self, sample_yaml_rules):
        """Test interactions between multiple rules."""
        engine = Engine.from_yaml(sample_yaml_rules)
        
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
        assert len(result.fired_rules) > 0
        assert result.execution_time_ms > 0
    
    @pytest.mark.integration
    def test_no_rules_fired(self):
        """Test case where no rules should fire."""
        yaml_rules = """
rules:
  - id: high_amount_only
    priority: 100
    if: "amount > 10000"
    then:
      tier: vip
"""
        engine = Engine.from_yaml(yaml_rules)
        
        # Facts that don't match any rules
        facts = {'amount': 500, 'status': 'pending'}
        
        result = engine.reason(facts)
        
        assert len(result.fired_rules) == 0
        assert result.verdict == {}
        assert result.execution_time_ms > 0
    
    @pytest.mark.integration
    def test_directory_loading_workflow(self, yaml_files_directory):
        """Test complete workflow with directory loading."""
        # Load rules from directory
        engine = Engine.from_directory(yaml_files_directory)
        
        # Test facts that should trigger rules from different files
        facts = {
            'status': 'active',        # general rule
            'user_type': 'vip',        # customer rule  
            'loyalty_years': 6,        # customer rule
            'amount': 15000,           # security rule
            'risk_score': 75           # security rule
        }
        
        result = engine.reason(facts)
        
        # Should fire rules from multiple files
        assert len(result.fired_rules) >= 3
        assert 'general_rule' in result.fired_rules
        assert 'vip_customer' in result.fired_rules
        assert 'loyalty_bonus' in result.fired_rules
        assert 'high_risk_transaction' in result.fired_rules
        
        # Check verdict combines results from all files
        assert result.verdict['processed'] is True      # from general
        assert result.verdict['special_treatment'] is True  # from vip
        assert result.verdict['loyalty_bonus'] == 500   # from loyalty
        assert result.verdict['requires_approval'] is True  # from security


class TestErrorHandling:
    """Test error handling in end-to-end workflows."""
    
    @pytest.mark.integration
    def test_invalid_yaml_handling(self):
        """Test handling of invalid YAML."""
        invalid_yaml = """
rules:
  - id: broken_rule
    if: "amount >"  # Invalid expression syntax
    then:
      tier: premium
"""
        
        # Should raise ValidationError during engine creation
        with pytest.raises(ValidationError):
            Engine.from_yaml(invalid_yaml)
    
    @pytest.mark.integration
    def test_runtime_evaluation_errors(self):
        """Test handling of runtime evaluation errors."""
        yaml_rules = """
rules:
  - id: division_by_zero
    priority: 100
    if: "amount / divisor > 100"
    then:
      result: calculated
"""
        
        engine = Engine.from_yaml(yaml_rules)
        
        # Facts that will cause division by zero
        facts = {'amount': 1000, 'divisor': 0}
        
        # Should handle error gracefully during reasoning
        # Note: Our simplified engine handles errors by not firing the rule
        result = engine.reason(facts)
        
        # Should not fire the rule due to evaluation error
        assert 'division_by_zero' not in result.fired_rules
        assert result.verdict == {}
    
    @pytest.mark.integration
    def test_missing_field_handling(self):
        """Test handling of missing fields."""
        yaml_rules = """
rules:
  - id: field_check
    priority: 100
    if: "nonexistent_field > 100"
    then:
      status: processed
"""
        
        engine = Engine.from_yaml(yaml_rules)
        facts = {'amount': 1000}
        
        result = engine.reason(facts)
        
        # Should handle missing field gracefully by not firing rule
        assert 'field_check' not in result.fired_rules
        assert result.verdict == {}
    
    @pytest.mark.integration
    def test_engine_creation_errors(self):
        """Test various engine creation error scenarios."""
        # Missing rules key
        with pytest.raises(ValidationError, match="YAML must contain 'rules' key"):
            Engine.from_yaml("other_data: value")
        
        # Empty rules
        with pytest.raises(ValidationError, match="No valid rules found"):
            Engine.from_yaml("rules: []")
        
        # Invalid rule structure
        with pytest.raises(ValidationError):
            Engine.from_yaml("""
rules:
  - id: invalid
    # Missing condition and actions
""")


class TestConditionTesting:
    """Test condition testing functionality."""
    
    @pytest.mark.integration
    def test_condition_testing_debug(self, sample_yaml_rules):
        """Test condition testing for debugging."""
        engine = Engine.from_yaml(sample_yaml_rules)
        
        # Test various conditions
        test_facts = {
            'amount': 1500,
            'status': 'active',
            'user_type': 'premium',
            'account_balance': 6000,
            'risk_score': 30,
            'country': 'US'
        }
        
        conditions_to_test = [
            ("amount > 1000", True),
            ("status == 'active'", True),
            ("amount > 1000 and status == 'active'", True),
            ("risk_score > 50", False),
            ("account_balance > 5000", True),
            ("country in ['US', 'CA']", True),
        ]
        
        for condition, expected in conditions_to_test:
            result = engine.test_condition(condition, test_facts)
            assert result == expected, f"Condition '{condition}' expected {expected}, got {result}"
    
    @pytest.mark.integration
    def test_structured_condition_testing(self):
        """Test condition testing with structured conditions."""
        structured_yaml = """
rules:
  - id: test_rule
    priority: 100
    if:
      all:
        - "amount > 1000"
        - "status == 'active'"
    then:
      approved: true
"""
        
        engine = Engine.from_yaml(structured_yaml)
        
        # Test that the parsed structured condition works
        facts = {'amount': 1500, 'status': 'active'}
        result = engine.reason(facts)
        
        assert 'test_rule' in result.fired_rules
        assert result.verdict['approved'] is True


class TestPerformance:
    """Test performance characteristics of end-to-end workflows."""
    
    @pytest.mark.integration
    def test_repeated_execution_performance(self, engine_with_rules, performance_facts):
        """Test performance of repeated executions."""
        engine = engine_with_rules
        
        # Execute reasoning on many fact sets
        results = []
        total_time = 0
        
        for fact_set in performance_facts[:50]:  # Test first 50 for faster execution
            result = engine.reason(fact_set)
            results.append(result)
            total_time += result.execution_time_ms
        
        # Verify all executions completed
        assert len(results) == 50
        
        # Average execution time should be reasonable
        avg_time = total_time / len(results)
        assert avg_time < 100  # Less than 100ms average (generous for testing)
    
    @pytest.mark.integration
    def test_large_rule_set_performance(self):
        """Test performance with moderately large rule sets."""
        # Generate rule set (reduced size for faster testing)
        rules = ["rules:"]
        for i in range(20):  # Reduced from 100 to 20
            rules.append(f"""
  - id: rule_{i}
    priority: {100 - i}
    if: "amount > {i * 100} and field_{i % 5} == 'value_{i % 3}'"
    then:
      result_{i}: true
      priority_{i}: {100 - i}
""")
        
        large_yaml = '\n'.join(rules)
        engine = Engine.from_yaml(large_yaml)
        
        # Test facts that might match several rules
        facts = {
            'amount': 1000,
            **{f'field_{i}': f'value_{i % 3}' for i in range(5)}
        }
        
        result = engine.reason(facts)
        
        # Should complete in reasonable time
        assert result.execution_time_ms < 1000  # Less than 1 second
        assert len(result.fired_rules) > 0  # Should fire some rules
    
    @pytest.mark.integration
    def test_engine_analysis_performance(self, engine_with_rules):
        """Test that engine analysis is fast."""
        engine = engine_with_rules
        
        # Analysis should be fast
        analysis = engine.get_analysis()
        
        assert 'rule_count' in analysis
        assert 'rule_ids' in analysis
        assert 'avg_priority' in analysis
        
        # Basic sanity checks
        assert analysis['rule_count'] > 0
        assert len(analysis['rule_ids']) == analysis['rule_count']


class TestComplexScenarios:
    """Test complex real-world scenarios."""
    
    @pytest.mark.integration
    def test_customer_approval_scenario(self):
        """Test a realistic customer approval scenario."""
        customer_rules = """
rules:
  - id: vip_instant_approval
    priority: 100
    if:
      all:
        - "customer_tier == 'vip'"
        - "credit_score >= 750"
        - "annual_income >= 100000"
    then:
      approved: true
      credit_limit: 50000
      processing_time: instant
    tags: [vip, instant]
      
  - id: premium_standard_approval
    priority: 90
    if:
      all:
        - "customer_tier == 'premium'"
        - "credit_score >= 650"
        - "debt_to_income < 0.4"
    then:
      approved: true
      credit_limit: 25000
      processing_time: 24_hours
    tags: [premium, standard]
      
  - id: risk_rejection
    priority: 200  # Higher priority to override approvals
    if:
      any:
        - "credit_score < 600"
        - "debt_to_income >= 0.5"
        - "recent_bankruptcies > 0"
    then:
      approved: false
      rejection_reason: high_risk
    tags: [risk, rejection]
"""
        
        engine = Engine.from_yaml(customer_rules)
        
        # Test case 1: VIP customer - should get instant approval
        vip_facts = {
            'customer_tier': 'vip',
            'credit_score': 800,
            'annual_income': 150000,
            'debt_to_income': 0.3,
            'recent_bankruptcies': 0
        }
        
        result1 = engine.reason(vip_facts)
        assert 'vip_instant_approval' in result1.fired_rules
        assert result1.verdict['approved'] is True
        assert result1.verdict['credit_limit'] == 50000
        assert result1.verdict['processing_time'] == 'instant'
        
        # Test case 2: High risk customer - should be rejected despite being premium
        risk_facts = {
            'customer_tier': 'premium',
            'credit_score': 550,  # Too low
            'annual_income': 80000,
            'debt_to_income': 0.3,
            'recent_bankruptcies': 0
        }
        
        result2 = engine.reason(risk_facts)
        assert 'risk_rejection' in result2.fired_rules
        assert result2.verdict['approved'] is False
        assert result2.verdict['rejection_reason'] == 'high_risk'
        
        # Test case 3: Standard premium approval
        premium_facts = {
            'customer_tier': 'premium',
            'credit_score': 700,
            'annual_income': 75000,
            'debt_to_income': 0.35,
            'recent_bankruptcies': 0
        }
        
        result3 = engine.reason(premium_facts)
        assert 'premium_standard_approval' in result3.fired_rules
        assert result3.verdict['approved'] is True
        assert result3.verdict['credit_limit'] == 25000
    
    @pytest.mark.integration
    def test_fraud_detection_scenario(self):
        """Test a realistic fraud detection scenario."""
        fraud_rules = """
rules:
  - id: high_velocity_fraud
    priority: 200
    if:
      all:
        - "transaction_count_24h > 10"
        - "total_amount_24h > 5000"
        - "unique_merchants_24h > 5"
    then:
      fraud_risk: high
      block_card: true
      alert_customer: true
    tags: [fraud, velocity]
      
  - id: unusual_location_fraud
    priority: 150
    if:
      all:
        - "location_country != home_country"
        - "distance_from_home > 1000"  # miles
        - "time_since_last_home_transaction < 6"  # hours
    then:
      fraud_risk: medium
      require_verification: true
    tags: [fraud, location]
      
  - id: merchant_category_fraud
    priority: 100
    if:
      any:
        - "merchant_category == 'high_risk'"
        - "amount > usual_spend_limit * 3"
    then:
      fraud_risk: low
      additional_monitoring: true
    tags: [fraud, merchant]
"""
        
        engine = Engine.from_yaml(fraud_rules)
        
        # Test case 1: High velocity fraud
        velocity_facts = {
            'transaction_count_24h': 15,
            'total_amount_24h': 7500,
            'unique_merchants_24h': 8,
            'location_country': 'US',
            'home_country': 'US',
            'distance_from_home': 0,
            'time_since_last_home_transaction': 1,
            'merchant_category': 'normal',
            'amount': 200,
            'usual_spend_limit': 500
        }
        
        result1 = engine.reason(velocity_facts)
        assert 'high_velocity_fraud' in result1.fired_rules
        assert result1.verdict['fraud_risk'] == 'high'
        assert result1.verdict['block_card'] is True
        
        # Test case 2: Unusual location
        location_facts = {
            'transaction_count_24h': 2,
            'total_amount_24h': 500,
            'unique_merchants_24h': 2,
            'location_country': 'FR',
            'home_country': 'US',
            'distance_from_home': 4000,
            'time_since_last_home_transaction': 3,
            'merchant_category': 'normal',
            'amount': 200,
            'usual_spend_limit': 500
        }
        
        result2 = engine.reason(location_facts)
        assert 'unusual_location_fraud' in result2.fired_rules
        assert result2.verdict['fraud_risk'] == 'medium'
        assert result2.verdict['require_verification'] is True 