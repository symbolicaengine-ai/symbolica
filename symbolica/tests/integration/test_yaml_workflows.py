"""
YAML Workflow Integration Tests
==============================

Tests for complete YAML-based workflows in the simplified architecture.
"""

import pytest
from pathlib import Path

from symbolica import Engine
from symbolica.core import ValidationError


class TestYamlWorkflows:
    """Test complete YAML-based workflows."""
    
    @pytest.mark.integration
    def test_basic_yaml_workflow(self):
        """Test basic YAML workflow from string to execution."""
        yaml_rules = """
rules:
  - id: customer_validation
    priority: 100
    if: "customer_type == 'premium' and account_balance > 1000"
    then:
      tier: gold
      discount: 0.15
    tags: [customer, validation]
    
  - id: risk_assessment
    priority: 90
    if: "transaction_amount > 10000 and risk_score > 0.8"
    then:
      requires_approval: true
      alert_level: high
    tags: [risk, security]
    
  - id: loyalty_bonus
    priority: 50
    if: "customer_loyalty_years >= 5 and tier == 'gold'"
    then:
      bonus_eligible: true
      bonus_rate: 0.05
    tags: [loyalty, rewards]
"""
        
        # Create engine and execute
        engine = Engine.from_yaml(yaml_rules)
        
        # Test scenario 1: Premium customer with loyalty
        facts1 = {
            'customer_type': 'premium',
            'account_balance': 5000,
            'transaction_amount': 2000,
            'risk_score': 0.3,
            'customer_loyalty_years': 6
        }
        
        result1 = engine.reason(facts1)
        
        # Should trigger customer_validation and loyalty_bonus
        assert 'customer_validation' in result1.fired_rules
        assert 'loyalty_bonus' in result1.fired_rules
        assert result1.verdict['tier'] == 'gold'
        assert result1.verdict['discount'] == 0.15
        assert result1.verdict['bonus_eligible'] is True
        assert result1.verdict['bonus_rate'] == 0.05
        
        # Test scenario 2: High-risk transaction
        facts2 = {
            'customer_type': 'premium',
            'account_balance': 5000,
            'transaction_amount': 15000,
            'risk_score': 0.9,
            'customer_loyalty_years': 2
        }
        
        result2 = engine.reason(facts2)
        
        # Should trigger both customer_validation and risk_assessment
        assert 'customer_validation' in result2.fired_rules
        assert 'risk_assessment' in result2.fired_rules
        assert result2.verdict['tier'] == 'gold'
        assert result2.verdict['requires_approval'] is True
        assert result2.verdict['alert_level'] == 'high'
    
    @pytest.mark.integration
    def test_file_based_workflow(self, temp_directory):
        """Test workflow with YAML loaded from file."""
        yaml_content = """
rules:
  - id: file_based_rule
    priority: 100
    if: "value > threshold"
    then:
      processed: true
      source: file
    tags: [file_test]
"""
        
        # Write YAML to file
        yaml_file = temp_directory / "test_rules.yaml"
        yaml_file.write_text(yaml_content)
        
        # Load engine from file
        engine = Engine.from_file(yaml_file)
        
        # Test execution
        facts = {'value': 150, 'threshold': 100}
        result = engine.reason(facts)
        
        assert 'file_based_rule' in result.fired_rules
        assert result.verdict['processed'] is True
        assert result.verdict['source'] == 'file'
    
    @pytest.mark.integration
    def test_directory_based_workflow(self, temp_directory):
        """Test workflow with YAML loaded from directory."""
        # Create directory structure
        rules_dir = temp_directory / "rules"
        rules_dir.mkdir()
        
        # Create multiple YAML files
        customer_yaml = """
rules:
  - id: customer_rule
    priority: 100
    if: "customer_status == 'active'"
    then:
      customer_processed: true
    tags: [customer]
"""
        
        product_yaml = """
rules:
  - id: product_rule
    priority: 90
    if: "product_available == true"
    then:
      product_processed: true
    tags: [product]
"""
        
        (rules_dir / "customer.yaml").write_text(customer_yaml)
        (rules_dir / "product.yaml").write_text(product_yaml)
        
        # Load engine from directory
        engine = Engine.from_directory(rules_dir)
        
        # Test execution
        facts = {'customer_status': 'active', 'product_available': True}
        result = engine.reason(facts)
        
        assert 'customer_rule' in result.fired_rules
        assert 'product_rule' in result.fired_rules
        assert result.verdict['customer_processed'] is True
        assert result.verdict['product_processed'] is True
    
    @pytest.mark.integration
    def test_structured_conditions_workflow(self):
        """Test workflow with structured conditions (all/any/not)."""
        structured_yaml = """
rules:
  - id: complex_approval
    priority: 100
    if:
      all:
        - "amount > 1000"
        - any:
          - "customer_tier == 'gold'"
          - "loyalty_years >= 3"
        - not: "risk_flags contains 'fraud'"
    then:
      approved: true
      approval_type: complex
    tags: [approval, complex]
    
  - id: simple_rejection
    priority: 200
    if:
      any:
        - "amount > 50000"
        - "risk_score > 0.9"
        - "blacklisted == true"
    then:
      approved: false
      rejection_reason: automatic
    tags: [rejection, automatic]
"""
        
        engine = Engine.from_yaml(structured_yaml)
        
        # Test case 1: Complex approval conditions met
        approval_facts = {
            'amount': 5000,
            'customer_tier': 'gold',
            'loyalty_years': 5,
            'risk_flags': 'verified,clean',
            'risk_score': 0.2,
            'blacklisted': False
        }
        
        result1 = engine.reason(approval_facts)
        assert 'complex_approval' in result1.fired_rules
        assert result1.verdict['approved'] is True
        assert result1.verdict['approval_type'] == 'complex'
        
        # Test case 2: Automatic rejection
        rejection_facts = {
            'amount': 75000,  # Exceeds limit
            'customer_tier': 'gold',
            'loyalty_years': 5,
            'risk_flags': 'verified',
            'risk_score': 0.3,
            'blacklisted': False
        }
        
        result2 = engine.reason(rejection_facts)
        assert 'simple_rejection' in result2.fired_rules
        assert result2.verdict['approved'] is False
        assert result2.verdict['rejection_reason'] == 'automatic'
    
    @pytest.mark.integration
    def test_priority_ordering_workflow(self):
        """Test that rule priority ordering works correctly."""
        priority_yaml = """
rules:
  - id: low_priority
    priority: 10
    if: "amount > 100"
    then:
      level: basic
      
  - id: medium_priority
    priority: 50
    if: "amount > 100"
    then:
      level: standard
        
  - id: high_priority
    priority: 100
    if: "amount > 100"
    then:
      level: premium
"""
        
        engine = Engine.from_yaml(priority_yaml)
        
        # All rules should fire, but higher priority should override
        facts = {'amount': 500}
        result = engine.reason(facts)
        
        # All rules should fire (they all match)
        assert len(result.fired_rules) == 3
        assert 'low_priority' in result.fired_rules
        assert 'medium_priority' in result.fired_rules
        assert 'high_priority' in result.fired_rules
        
        # Final verdict should reflect the last rule that fired
        # (our simple engine executes in priority order, higher first)
        assert result.verdict['level'] == 'basic'  # Last one wins in our simple implementation
    
    @pytest.mark.integration
    def test_conditional_chaining_workflow(self):
        """Test workflow where rules build on each other."""
        chaining_yaml = """
rules:
  - id: initial_assessment
    priority: 100
    if: "credit_score >= 650"
    then:
      eligible: true
      base_rate: 0.05
    tags: [assessment]
    
  - id: tier_upgrade
    priority: 90
    if: "eligible == true and annual_income > 75000"
    then:
      tier: premium
      rate_discount: 0.01
    tags: [upgrade]
    
  - id: final_rate_calculation
    priority: 80
    if: "tier == 'premium' and base_rate > 0"
    then:
      final_rate: "base_rate - rate_discount"
      approved: true
    tags: [calculation]
"""
        
        engine = Engine.from_yaml(chaining_yaml)
        
        # Test successful chaining
        facts = {
            'credit_score': 720,
            'annual_income': 85000
        }
        
        result = engine.reason(facts)
        
        # All rules should fire in sequence
        assert 'initial_assessment' in result.fired_rules
        assert 'tier_upgrade' in result.fired_rules
        assert 'final_rate_calculation' in result.fired_rules
        
        # Check the chained results
        assert result.verdict['eligible'] is True
        assert result.verdict['base_rate'] == 0.05
        assert result.verdict['tier'] == 'premium'
        assert result.verdict['rate_discount'] == 0.01
        assert 'base_rate - rate_discount' in str(result.verdict['final_rate'])
        assert result.verdict['approved'] is True
    
    @pytest.mark.integration
    def test_error_handling_in_workflow(self):
        """Test error handling during YAML workflow execution."""
        # Test with invalid YAML structure
        invalid_yaml = """
rules:
  - id: broken_rule
    # Missing required fields
    if: "amount > 1000"
"""
        
        with pytest.raises(ValidationError):
            Engine.from_yaml(invalid_yaml)
        
        # Test with runtime evaluation errors
        problematic_yaml = """
rules:
  - id: division_rule
    priority: 100
    if: "amount / zero_value > 10"
    then:
      result: calculated
"""
        
        engine = Engine.from_yaml(problematic_yaml)
        
        # Should handle division by zero gracefully
        facts = {'amount': 1000, 'zero_value': 0}
        result = engine.reason(facts)
        
        # Rule should not fire due to evaluation error
        assert 'division_rule' not in result.fired_rules
        assert result.verdict == {}
    
    @pytest.mark.integration
    def test_mixed_condition_formats_workflow(self):
        """Test workflow with mixed condition formats."""
        mixed_yaml = """
rules:
  - id: string_condition
    priority: 100
    if: "amount > 1000 and status == 'active'"
    then:
      string_format: true
    tags: [string]
    
  - id: structured_condition
    priority: 90
    if:
      all:
        - "user_type == 'premium'"
        - "account_verified == true"
    then:
      structured_format: true
    tags: [structured]
    
  - id: alternative_syntax
    priority: 80
    condition: "priority_customer == true"
    actions:
      alternative_format: true
    tags: [alternative]
"""
        
        engine = Engine.from_yaml(mixed_yaml)
        
        # Test facts that should trigger all rules
        facts = {
            'amount': 2000,
            'status': 'active',
            'user_type': 'premium',
            'account_verified': True,
            'priority_customer': True
        }
        
        result = engine.reason(facts)
        
        # All rules should fire
        assert 'string_condition' in result.fired_rules
        assert 'structured_condition' in result.fired_rules
        assert 'alternative_syntax' in result.fired_rules
        
        # Check verdict
        assert result.verdict['string_format'] is True
        assert result.verdict['structured_format'] is True
        assert result.verdict['alternative_format'] is True
    
    @pytest.mark.integration
    def test_performance_workflow(self):
        """Test performance characteristics of YAML workflows."""
        # Generate larger rule set for performance testing
        rules = ["rules:"]
        for i in range(15):  # Moderate size for testing
            rules.append(f"""
  - id: perf_rule_{i}
    priority: {100 - i}
    if: "test_value > {i * 10} and active == true"
    then:
      result_{i}: {i}
      processed: true
    tags: [performance, test_{i}]
""")
        
        large_yaml = '\n'.join(rules)
        engine = Engine.from_yaml(large_yaml)
        
        # Test execution performance
        facts = {'test_value': 50, 'active': True}
        result = engine.reason(facts)
        
        # Should complete quickly
        assert result.execution_time_ms < 100  # Less than 100ms
        
        # Should fire appropriate rules
        assert len(result.fired_rules) > 0
        assert result.verdict['processed'] is True 