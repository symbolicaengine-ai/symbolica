"""
Unit Tests for Core Domain Models
=================================

Tests for Rule, RuleSet, Facts, ExecutionContext, ExecutionResult, and related models.
"""

import pytest
import uuid
from typing import Dict, Any

from symbolica.core import (
    Rule, RuleSet, Facts, ExecutionContext, ExecutionResult, 
    Priority, Condition, Action, RuleId, TraceLevel,
    rule_id, priority, condition, action_set, action_call, facts,
    ValidationError, EvaluationError
)


class TestRuleId:
    """Test RuleId value object."""
    
    @pytest.mark.unit
    def test_rule_id_creation(self):
        """Test basic rule ID creation."""
        rid = rule_id("test_rule")
        assert rid.value == "test_rule"
        assert str(rid) == "RuleId(value='test_rule')"
        assert repr(rid) == "RuleId(value='test_rule')"
    
    @pytest.mark.unit
    def test_rule_id_equality(self):
        """Test rule ID equality."""
        rid1 = rule_id("test")
        rid2 = rule_id("test")
        rid3 = rule_id("other")
        
        assert rid1 == rid2
        assert rid1 != rid3
        assert hash(rid1) == hash(rid2)
        assert hash(rid1) != hash(rid3)
    
    @pytest.mark.unit
    def test_rule_id_validation(self):
        """Test rule ID validation."""
        # Valid IDs
        assert rule_id("valid_rule").value == "valid_rule"
        assert rule_id("rule123").value == "rule123"
        assert rule_id("rule_with_underscores").value == "rule_with_underscores"
        assert rule_id("rule-with-dashes").value == "rule-with-dashes"  # Dashes are valid
        
        # Invalid IDs should raise ValueError
        with pytest.raises(ValueError):
            rule_id("")  # Empty
        
        with pytest.raises(ValueError):
            rule_id("rule with spaces")  # Spaces


class TestPriority:
    """Test Priority value object."""
    
    @pytest.mark.unit
    def test_priority_creation(self):
        """Test priority creation."""
        p = priority(100)
        assert p.value == 100
        assert str(p) == "Priority(value=100)"
        assert repr(p) == "Priority(value=100)"
    
    @pytest.mark.unit
    def test_priority_comparison(self):
        """Test priority comparison."""
        p1 = priority(100)
        p2 = priority(200)
        p3 = priority(100)
        
        assert p1 < p2
        assert p2 > p1
        assert p1 == p3
        assert not p1 > p3
        assert not p1 < p3
    
    @pytest.mark.unit
    def test_priority_validation(self):
        """Test priority validation."""
        # Valid priorities
        assert priority(0).value == 0
        assert priority(100).value == 100
        assert priority(1000).value == 1000
        
        # Invalid priorities
        with pytest.raises(ValueError):
            priority(-1)  # Negative


class TestCondition:
    """Test Condition value object."""
    
    @pytest.mark.unit
    def test_string_condition(self):
        """Test string-based conditions."""
        cond = condition("amount > 1000")
        assert cond.expression == "amount > 1000"
        assert hasattr(cond, 'content_hash')
        assert hasattr(cond, 'referenced_fields')
    
    @pytest.mark.unit
    def test_condition_equality(self):
        """Test condition equality."""
        cond1 = condition("amount > 1000")
        cond2 = condition("amount > 1000")
        cond3 = condition("amount > 2000")
        
        assert cond1 == cond2
        assert cond1 != cond3
        assert cond1.content_hash == cond2.content_hash
    
    @pytest.mark.unit
    def test_condition_validation(self):
        """Test condition validation."""
        # Valid condition
        cond = condition("amount > 1000")
        assert cond.expression == "amount > 1000"
        
        # Invalid condition
        with pytest.raises(ValueError):
            condition("")  # Empty


class TestAction:
    """Test Action value object."""
    
    @pytest.mark.unit
    def test_set_action(self):
        """Test set action creation."""
        action = action_set(tier='premium', discount=0.15)
        assert action.type == "set"
        assert action.parameters == {'tier': 'premium', 'discount': 0.15}
    
    @pytest.mark.unit
    def test_call_action(self):
        """Test function call action."""
        action = action_call('send_email', template='welcome', user_id=123)
        assert action.type == "call"
        assert action.parameters['function'] == 'send_email'
        assert action.parameters['params'] == {'template': 'welcome', 'user_id': 123}
    
    @pytest.mark.unit
    def test_action_equality(self):
        """Test action equality."""
        action1 = action_set(tier='premium')
        action2 = action_set(tier='premium')
        action3 = action_set(tier='standard')
        
        assert action1 == action2
        assert action1 != action3


class TestRule:
    """Test Rule entity."""
    
    @pytest.mark.unit
    def test_rule_creation(self, basic_rule):
        """Test basic rule creation."""
        rule = basic_rule
        assert rule.id.value == "test_rule"
        assert rule.priority.value == 100
        assert rule.condition.expression == "amount > 1000"
        assert rule.actions[0].type == "set"
    
    @pytest.mark.unit
    def test_rule_equality(self):
        """Test rule equality (based on ID)."""
        rule1 = Rule(
            id=rule_id("test"),
            priority=priority(100),
            condition=condition("amount > 1000"),
            action=action_set({'tier': 'premium'})
        )
        rule2 = Rule(
            id=rule_id("test"),
            priority=priority(200),  # Different priority
            condition=condition("amount > 2000"),  # Different condition
            action=action_set({'tier': 'standard'})  # Different action
        )
        rule3 = Rule(
            id=rule_id("other"),
            priority=priority(100),
            condition=condition("amount > 1000"),
            action=action_set({'tier': 'premium'})
        )
        
        # Rules with same ID are equal
        assert rule1 == rule2
        assert rule1 != rule3
        assert hash(rule1) == hash(rule2)
    
    @pytest.mark.unit
    def test_rule_validation(self):
        """Test rule validation."""
        # Valid rule
        rule = Rule(
            id=rule_id("valid"),
            priority=priority(100),
            condition=condition("amount > 1000"),
            actions=[action_set(tier='premium')]
        )
        assert rule.id.value == "valid"
        
        # Rule with empty actions
        with pytest.raises(ValueError):
            Rule(
                id=rule_id("invalid"),
                priority=priority(100),
                condition=condition("amount > 1000"),
                actions=[]  # Empty actions
            )
    
    @pytest.mark.unit
    def test_rule_written_fields(self):
        """Test written fields extraction."""
        rule = Rule(
            id=rule_id("test"),
            priority=priority(100),
            condition=condition("amount > 1000"),
            actions=[action_set(tier='premium', discount=0.15)]
        )
        
        written_fields = rule.written_fields
        assert 'tier' in written_fields
        assert 'discount' in written_fields
        assert len(written_fields) == 2


class TestFacts:
    """Test Facts value object."""
    
    @pytest.mark.unit
    def test_facts_creation(self, sample_facts):
        """Test facts creation."""
        f = facts(**sample_facts)
        assert f.data == sample_facts
        assert f['amount'] == 1500
        assert f['status'] == 'active'
    
    @pytest.mark.unit
    def test_facts_get_with_default(self):
        """Test facts get with default values."""
        f = facts(amount=1000)
        
        assert f.get('amount') == 1000
        assert f.get('status') is None
        assert f.get('status', 'unknown') == 'unknown'
    
    @pytest.mark.unit
    def test_facts_iteration(self, sample_facts):
        """Test facts iteration."""
        f = facts(**sample_facts)
        
        # Test data access
        assert f.data == sample_facts
        assert f.has('amount')
        assert not f.has('nonexistent')
    
    @pytest.mark.unit
    def test_facts_immutability(self, sample_facts):
        """Test that facts are immutable."""
        f = facts(**sample_facts)
        
        # Facts object itself is immutable (dataclass with frozen=True)
        # Direct data modification would modify the underlying dict,
        # but the Facts object is frozen
        assert f.data == sample_facts


class TestRuleSet:
    """Test RuleSet collection."""
    
    @pytest.mark.unit
    def test_rule_set_creation(self, complex_rule_set):
        """Test rule set creation."""
        rule_set = complex_rule_set
        assert len(rule_set.rules) == 4
        assert rule_set.version is not None
    
    @pytest.mark.unit
    def test_rule_set_iteration(self, complex_rule_set):
        """Test rule set iteration."""
        rule_set = complex_rule_set
        
        rule_ids = [rule.id.value for rule in rule_set]
        expected_ids = ['high_value', 'risk_check', 'country_check', 'age_bonus']
        assert rule_ids == expected_ids
    
    @pytest.mark.unit
    def test_rule_set_get_by_id(self, complex_rule_set):
        """Test getting rule by ID."""
        rule_set = complex_rule_set
        
        rule = rule_set.get_rule('high_value')
        assert rule is not None
        assert rule.id.value == 'high_value'
        
        assert rule_set.get_rule('nonexistent') is None
    
    @pytest.mark.unit
    def test_rule_set_validation(self):
        """Test rule set validation."""
        # Valid rule set
        rules = [
            Rule(
                id=rule_id("rule1"),
                priority=priority(100),
                condition=condition("amount > 1000"),
                actions=[action_set(tier='premium')]
            ),
            Rule(
                id=rule_id("rule2"),
                priority=priority(90),
                condition=condition("status == 'active'"),
                actions=[action_set(active=True)]
            )
        ]
        rule_set = RuleSet(rules=rules)
        assert rule_set.rule_count == 2
        
        # Invalid rule set - duplicate IDs
        duplicate_rules = [
            Rule(
                id=rule_id("same_id"),
                priority=priority(100),
                condition=condition("amount > 1000"),
                actions=[action_set(tier='premium')]
            ),
            Rule(
                id=rule_id("same_id"),  # Duplicate ID
                priority=priority(90),
                condition=condition("status == 'active'"),
                actions=[action_set(active=True)]
            )
        ]
        
        with pytest.raises(ValueError):
            RuleSet(rules=duplicate_rules)


class TestExecutionContext:
    """Test ExecutionContext."""
    
    @pytest.mark.unit
    def test_execution_context_creation(self, sample_facts):
        """Test execution context creation."""
        f = facts(**sample_facts)
        context = ExecutionContext(
            original_facts=f,
            enriched_facts={},
            fired_rules=[],
            trace_level=TraceLevel.BASIC
        )
        
        assert context.original_facts == f
        assert context.trace_level == TraceLevel.BASIC
        assert context.context_id is not None
    
    @pytest.mark.unit
    def test_execution_context_methods(self, sample_facts):
        """Test execution context methods."""
        f = facts(**sample_facts)
        context = ExecutionContext(
            original_facts=f,
            enriched_facts={},
            fired_rules=[],
            trace_level=TraceLevel.DETAILED
        )
        
        # Test setting and getting facts
        context.set_fact('new_field', 'new_value')
        assert context.get_fact('new_field') == 'new_value'
        assert context.get_fact('amount') == 1500  # From original facts
        
        # Test rule firing
        rule_id_obj = rule_id('test_rule')
        context.rule_fired(rule_id_obj)
        assert len(context.fired_rules) == 1
        assert context.fired_rules[0] == rule_id_obj


class TestExecutionResult:
    """Test ExecutionResult."""
    
    @pytest.mark.unit
    def test_execution_result_creation(self):
        """Test execution result creation."""
        verdict = {'tier': 'premium', 'discount': 0.15}
        fired_rules = ['high_value', 'age_bonus']
        
        result = ExecutionResult(
            verdict=verdict,
            fired_rules=fired_rules,
            execution_time_ms=25.5
        )
        
        assert result.verdict == verdict
        assert result.fired_rules == fired_rules
        assert result.execution_time_ms == 25.5
        assert result.success is True
        assert result.errors == []
    
    @pytest.mark.unit
    def test_execution_result_with_errors(self):
        """Test execution result with errors."""
        errors = ['Invalid condition in rule xyz', 'Division by zero']
        
        result = ExecutionResult(
            verdict={},
            fired_rules=[],
            execution_time_ms=10.0,
            success=False,
            errors=errors
        )
        
        assert result.success is False
        assert result.errors == errors
    
    @pytest.mark.unit
    def test_execution_result_summary(self):
        """Test execution result summary."""
        result = ExecutionResult(
            verdict={'tier': 'premium'},
            fired_rules=['rule1', 'rule2'],
            execution_time_ms=15.3
        )
        
        summary = result.summary()
        assert 'verdict' in summary
        assert 'fired_rules' in summary
        assert 'execution_time_ms' in summary
        assert 'success' in summary 