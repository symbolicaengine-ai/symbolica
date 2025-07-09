"""
Rule Chaining Tests
==================

Tests for rule chaining functionality where rules can trigger other rules.
"""

import pytest
from symbolica import Engine, facts
from symbolica.core import ValidationError


class TestBasicRuleChaining:
    """Test basic rule chaining functionality."""
    
    @pytest.mark.unit
    def test_simple_chaining(self):
        """Test basic rule chaining where one rule triggers another."""
        yaml_rules = """
rules:
  - id: primary_rule
    priority: 100
    condition: "amount > 1000"
    actions:
      tier: premium
    triggers: [secondary_rule]
    
  - id: secondary_rule
    priority: 50
    condition: "tier == 'premium'"
    actions:
      discount: 0.1
      status: approved
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(amount=1500))
        
        # Both rules should fire
        assert len(result.fired_rules) == 2
        assert 'primary_rule' in result.fired_rules
        assert 'secondary_rule' in result.fired_rules
        
        # Check final verdict
        assert result.verdict['tier'] == 'premium'
        assert result.verdict['discount'] == 0.1
        assert result.verdict['status'] == 'approved'
        
        # Check reasoning shows triggering relationship
        assert 'triggered by primary_rule' in result.reasoning
    
    @pytest.mark.unit
    def test_multiple_triggers(self):
        """Test a rule triggering multiple other rules."""
        yaml_rules = """
rules:
  - id: main_rule
    priority: 100
    condition: "customer_type == 'vip'"
    actions:
      status: active
    triggers: [bonus_rule, notification_rule]
    
  - id: bonus_rule
    priority: 50
    condition: "status == 'active'"
    actions:
      bonus: 100
      
  - id: notification_rule
    priority: 50
    condition: "status == 'active'"
    actions:
      notify: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(customer_type='vip'))
        
        # All three rules should fire
        assert len(result.fired_rules) == 3
        assert 'main_rule' in result.fired_rules
        assert 'bonus_rule' in result.fired_rules
        assert 'notification_rule' in result.fired_rules
        
        # Check final verdict
        assert result.verdict['status'] == 'active'
        assert result.verdict['bonus'] == 100
        assert result.verdict['notify'] is True
    
    @pytest.mark.unit
    def test_chain_of_triggers(self):
        """Test a chain of rule triggers (A -> B -> C)."""
        yaml_rules = """
rules:
  - id: rule_a
    priority: 100
    condition: "level == 1"
    actions:
      level: 2
    triggers: [rule_b]
    
  - id: rule_b
    priority: 50
    condition: "level == 2"
    actions:
      level: 3
    triggers: [rule_c]
      
  - id: rule_c
    priority: 25
    condition: "level == 3"
    actions:
      final: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(level=1))
        
        # All three rules should fire in sequence
        assert len(result.fired_rules) == 3
        assert 'rule_a' in result.fired_rules
        assert 'rule_b' in result.fired_rules
        assert 'rule_c' in result.fired_rules
        
        # Check final state
        assert result.verdict['level'] == 3
        assert result.verdict['final'] is True
        
        # Check reasoning shows the chain
        reasoning = result.reasoning
        assert 'triggered by rule_a' in reasoning
        assert 'triggered by rule_b' in reasoning
    
    @pytest.mark.unit
    def test_conditional_chaining(self):
        """Test that triggered rules still need their conditions to be met."""
        yaml_rules = """
rules:
  - id: trigger_rule
    priority: 100
    condition: "activate == True"
    actions:
      status: ready
    triggers: [conditional_rule]
    
  - id: conditional_rule
    priority: 50
    condition: "status == 'ready' and amount > 500"
    actions:
      approved: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        
        # Test case 1: Both conditions met
        result1 = engine.reason(facts(activate=True, amount=600))
        assert len(result1.fired_rules) == 2
        assert result1.verdict['approved'] is True
        
        # Test case 2: Trigger fires but conditional rule's condition not met
        result2 = engine.reason(facts(activate=True, amount=300))
        assert len(result2.fired_rules) == 1
        assert 'trigger_rule' in result2.fired_rules
        assert 'conditional_rule' not in result2.fired_rules
        assert 'approved' not in result2.verdict


class TestChainValidation:
    """Test validation of rule chaining."""
    
    @pytest.mark.unit
    def test_invalid_trigger_reference(self):
        """Test validation fails when rule references non-existent trigger."""
        yaml_rules = """
rules:
  - id: main_rule
    condition: "amount > 100"
    actions:
      status: active
    triggers: [nonexistent_rule]
"""
        
        with pytest.raises(ValidationError, match="triggers unknown rule 'nonexistent_rule'"):
            Engine.from_yaml(yaml_rules)
    
    @pytest.mark.unit
    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies in rule chains."""
        yaml_rules = """
rules:
  - id: rule_a
    condition: "step == 1"
    actions:
      step: 2
    triggers: [rule_b]
    
  - id: rule_b
    condition: "step == 2"
    actions:
      step: 1
    triggers: [rule_a]
"""
        
        with pytest.raises(ValidationError, match="Circular dependency detected"):
            Engine.from_yaml(yaml_rules)
    
    @pytest.mark.unit
    def test_self_trigger_prevention(self):
        """Test that a rule cannot trigger itself."""
        yaml_rules = """
rules:
  - id: self_trigger
    condition: "value > 0"
    actions:
      value: 1
    triggers: [self_trigger]
"""
        
        with pytest.raises(ValidationError, match="Circular dependency detected"):
            Engine.from_yaml(yaml_rules)
    
    @pytest.mark.unit
    def test_complex_circular_dependency(self):
        """Test detection of complex circular dependencies (A -> B -> C -> A)."""
        yaml_rules = """
rules:
  - id: rule_a
    condition: "stage == 'a'"
    actions:
      stage: b
    triggers: [rule_b]
    
  - id: rule_b
    condition: "stage == 'b'"
    actions:
      stage: c
    triggers: [rule_c]
      
  - id: rule_c
    condition: "stage == 'c'"
    actions:
      stage: a
    triggers: [rule_a]
"""
        
        with pytest.raises(ValidationError, match="Circular dependency detected"):
            Engine.from_yaml(yaml_rules)


class TestChainWithExistingFeatures:
    """Test rule chaining integration with existing features."""
    
    @pytest.mark.unit
    def test_chaining_with_priorities(self):
        """Test rule chaining respects priority ordering."""
        yaml_rules = """
rules:
  - id: low_priority_trigger
    priority: 10
    condition: "start == True"
    actions:
      triggered: true
    triggers: [high_priority_target]
    
  - id: high_priority_target
    priority: 100
    condition: "triggered == True"
    actions:
      result: success
      
  - id: independent_high_priority
    priority: 200
    condition: "start == True"
    actions:
      independent: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(start=True))
        
        # All rules should fire
        assert len(result.fired_rules) == 3
        
        # Check execution order respects dependencies
        # independent_high_priority should fire first due to highest priority
        # Then low_priority_trigger should fire
        # Then high_priority_target should fire (triggered)
        fired_order = result.fired_rules
        assert fired_order.index('independent_high_priority') < fired_order.index('low_priority_trigger')
        assert fired_order.index('low_priority_trigger') < fired_order.index('high_priority_target')
    
    @pytest.mark.unit
    def test_chaining_with_tags(self):
        """Test rule chaining works with tags."""
        yaml_rules = """
rules:
  - id: approval_rule
    condition: "amount > 1000"
    actions:
      approved: true
    tags: [approval, primary]
    triggers: [notification_rule]
    
  - id: notification_rule
    condition: "approved == True"
    actions:
      notify_customer: true
    tags: [notification, secondary]
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(amount=1500))
        
        # Both rules should fire
        assert len(result.fired_rules) == 2
        assert result.verdict['approved'] is True
        assert result.verdict['notify_customer'] is True
        
        # Verify tags are preserved in rules
        approval_rule = next(r for r in engine.rules if r.id == 'approval_rule')
        notification_rule = next(r for r in engine.rules if r.id == 'notification_rule')
        
        assert 'approval' in approval_rule.tags
        assert 'notification' in notification_rule.tags
    
    @pytest.mark.unit
    def test_chaining_with_field_dependencies(self):
        """Test rule chaining works alongside field-based dependencies."""
        yaml_rules = """
rules:
  - id: data_processor
    priority: 100
    condition: "raw_data != None"
    actions:
      processed_data: "cleaned"
    triggers: [validator_rule]
    
  - id: validator_rule
    priority: 50
    condition: "processed_data != None"
    actions:
      validated: true
      
  - id: field_dependent_rule
    priority: 75
    condition: "processed_data == 'cleaned'"
    actions:
      field_based: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(raw_data="input"))
        
        # All rules should fire
        assert len(result.fired_rules) == 3
        assert result.verdict['processed_data'] == 'cleaned'
        assert result.verdict['validated'] is True
        assert result.verdict['field_based'] is True


class TestChainReasoning:
    """Test reasoning and explanation for rule chaining."""
    
    @pytest.mark.unit
    def test_chain_reasoning_explanation(self):
        """Test that reasoning clearly shows chaining relationships."""
        yaml_rules = """
rules:
  - id: primary
    condition: "trigger == True"
    actions:
      primary_done: true
    triggers: [secondary]
    
  - id: secondary
    condition: "primary_done == True"
    actions:
      secondary_done: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(trigger=True))
        
        reasoning = result.reasoning
        
        # Should show both rules fired
        assert 'primary:' in reasoning
        assert 'secondary:' in reasoning
        
        # Should show triggering relationship
        assert 'triggered by primary' in reasoning
    
    @pytest.mark.unit
    def test_llm_context_with_chaining(self):
        """Test LLM context generation includes chaining information."""
        yaml_rules = """
rules:
  - id: initiator
    condition: "start == True"
    actions:
      initiated: true
    triggers: [follower]
    
  - id: follower
    condition: "initiated == True"
    actions:
      completed: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        result = engine.reason(facts(start=True))
        
        llm_context = result.get_llm_context()
        
        # Should include both rules in fired rules
        assert 'initiator' in llm_context['rules_fired']
        assert 'follower' in llm_context['rules_fired']
        
        # Should include final facts
        assert llm_context['final_facts']['initiated'] is True
        assert llm_context['final_facts']['completed'] is True
        
        # Reasoning should mention triggering
        assert 'triggered by' in llm_context['reasoning'] 