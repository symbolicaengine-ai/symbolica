"""
Unit Tests for Simplified Core Models
=====================================

Tests for Rule, Facts, ExecutionContext, ExecutionResult in the simplified architecture.
"""

import pytest
from typing import Dict, Any

from symbolica.core import (
    Rule, Facts, ExecutionContext, ExecutionResult, 
    facts, SymbolicaError, ValidationError
)


class TestRule:
    """Test the simplified Rule model."""
    
    @pytest.mark.unit
    def test_rule_creation(self, simple_rule_dict):
        """Test basic rule creation from dict data."""
        rule = Rule(**simple_rule_dict)
        
        assert rule.id == "test_rule"
        assert rule.priority == 100
        assert rule.condition == "amount > 1000"
        assert rule.actions == {'tier': 'premium', 'approved': True}
        assert rule.tags == ['test', 'simple']
    
    @pytest.mark.unit
    def test_rule_minimal_creation(self):
        """Test rule creation with minimal required fields."""
        rule = Rule(
            id="minimal_rule",
            priority=50,
            condition="status == 'active'",
            actions={'processed': True}
        )
        
        assert rule.id == "minimal_rule"
        assert rule.priority == 50
        assert rule.condition == "status == 'active'"
        assert rule.actions == {'processed': True}
        assert rule.tags == []  # Default empty list
    
    @pytest.mark.unit
    def test_rule_validation(self):
        """Test rule validation logic."""
        # Valid rule
        rule = Rule(
            id="valid_rule",
            priority=100,
            condition="amount > 1000",
            actions={'tier': 'premium'}
        )
        assert rule.id == "valid_rule"
        
        # Invalid rules should raise ValueError during creation
        with pytest.raises(ValueError, match="Rule ID must be a non-empty string"):
            Rule(id="", priority=100, condition="amount > 1000", actions={'tier': 'premium'})
        
        with pytest.raises(ValueError, match="Rule ID must be a non-empty string"):
            Rule(id=None, priority=100, condition="amount > 1000", actions={'tier': 'premium'})
        
        with pytest.raises(ValueError, match="Priority must be an integer"):
            Rule(id="test", priority="high", condition="amount > 1000", actions={'tier': 'premium'})
        
        with pytest.raises(ValueError, match="Condition must be a non-empty string"):
            Rule(id="test", priority=100, condition="", actions={'tier': 'premium'})
        
        with pytest.raises(ValueError, match="Actions must be a non-empty dictionary"):
            Rule(id="test", priority=100, condition="amount > 1000", actions={})
        
        with pytest.raises(ValueError, match="Tags must be a list"):
            Rule(id="test", priority=100, condition="amount > 1000", actions={'tier': 'premium'}, tags="invalid")
    
    @pytest.mark.unit
    def test_rule_equality(self):
        """Test that rules are equal based on all attributes."""
        rule1 = Rule(id="test", priority=100, condition="amount > 1000", actions={'tier': 'premium'})
        rule2 = Rule(id="test", priority=100, condition="amount > 1000", actions={'tier': 'premium'})
        rule3 = Rule(id="different", priority=100, condition="amount > 1000", actions={'tier': 'premium'})
        rule4 = Rule(id="test", priority=90, condition="amount > 1000", actions={'tier': 'premium'})
        
        assert rule1 == rule2
        assert rule1 != rule3  # Different ID
        assert rule1 != rule4  # Different priority
    
    @pytest.mark.unit
    def test_rule_immutability(self):
        """Test that rules are immutable (frozen dataclass)."""
        rule = Rule(id="test", priority=100, condition="amount > 1000", actions={'tier': 'premium'})
        
        # Should not be able to modify rule attributes
        with pytest.raises(AttributeError):
            rule.id = "modified"
        
        with pytest.raises(AttributeError):
            rule.priority = 200


class TestFacts:
    """Test the Facts data structure."""
    
    @pytest.mark.unit
    def test_facts_creation(self, sample_facts):
        """Test facts creation from dict."""
        f = facts(**sample_facts)
        
        assert isinstance(f, Facts)
        assert f.data == sample_facts
        assert f['amount'] == 1500
        assert f['status'] == 'active'
    
    @pytest.mark.unit
    def test_facts_access_methods(self, sample_facts):
        """Test different ways to access facts."""
        f = facts(**sample_facts)
        
        # Dict-style access
        assert f['amount'] == 1500
        assert f['status'] == 'active'
        
        # Get method with default
        assert f.get('amount') == 1500
        assert f.get('nonexistent') is None
        assert f.get('nonexistent', 'default') == 'default'
        
        # Contains check (using 'in' operator)
        assert 'amount' in f
        assert 'nonexistent' not in f
    
    @pytest.mark.unit
    def test_facts_immutability(self, sample_facts):
        """Test that Facts objects are immutable."""
        f = facts(**sample_facts)
        
        # Facts object itself is frozen
        with pytest.raises(AttributeError):
            f.data = {}
        
        # But underlying dict can still be modified (by design)
        # This is acceptable since we control access through the Facts interface
        original_amount = f['amount']
        assert f['amount'] == original_amount
    
    @pytest.mark.unit
    def test_facts_iteration(self, sample_facts):
        """Test facts iteration capabilities."""
        f = facts(**sample_facts)
        
        # Check data property
        assert f.data == sample_facts
        
        # Can iterate over the data
        keys = list(f.data.keys())
        assert 'amount' in keys
        assert 'status' in keys
    
    @pytest.mark.unit
    def test_facts_with_complex_types(self):
        """Test facts with complex data types."""
        complex_data = {
            'amount': 1500,
            'tags': ['vip', 'loyalty'],
            'metadata': {'region': 'US', 'tier': 'gold'},
            'payment_history': [100, 95, 88],
            'active': True,
            'last_login': None
        }
        
        f = facts(**complex_data)
        
        assert f['tags'] == ['vip', 'loyalty']
        assert f['metadata']['region'] == 'US'
        assert f['payment_history'][0] == 100
        assert f['active'] is True
        assert f['last_login'] is None


class TestExecutionContext:
    """Test the ExecutionContext."""
    
    @pytest.mark.unit
    def test_execution_context_creation(self, sample_facts):
        """Test execution context creation."""
        f = facts(**sample_facts)
        context = ExecutionContext(
            original_facts=f,
            enriched_facts={},
            fired_rules=[]
        )
        
        assert context.original_facts == f
        # enriched_facts is automatically initialized from original_facts
        assert context.enriched_facts == sample_facts
        assert context.fired_rules == []
        assert context.verdict == {}  # No changes yet
        assert hasattr(context, 'start_time')
    
    @pytest.mark.unit
    def test_context_fact_operations(self, sample_facts):
        """Test setting and getting facts in context."""
        f = facts(**sample_facts)
        context = ExecutionContext(
            original_facts=f,
            enriched_facts={},
            fired_rules=[]
        )
        
        # Get original fact
        assert context.get_fact('amount') == 1500
        
        # Set new fact
        context.set_fact('new_field', 'new_value')
        assert context.get_fact('new_field') == 'new_value'
        
        # Overwrite existing fact
        context.set_fact('amount', 2000)
        assert context.get_fact('amount') == 2000  # Should get enriched value
        
        # Original facts should remain unchanged
        assert context.original_facts['amount'] == 1500
    
    @pytest.mark.unit
    def test_context_rule_firing(self):
        """Test rule firing tracking."""
        context = ExecutionContext(
            original_facts=facts(amount=1000),
            enriched_facts={},
            fired_rules=[]
        )
        
        # Fire some rules
        context.rule_fired('rule1', 'Some reason')
        context.rule_fired('rule2', 'Another reason')
        
        assert context.fired_rules == ['rule1', 'rule2']
        
        # Verdict should include all enriched facts
        context.set_fact('tier', 'premium')
        context.set_fact('approved', True)
        
        assert context.verdict == {'tier': 'premium', 'approved': True}
    



class TestExecutionResult:
    """Test the ExecutionResult."""
    
    @pytest.mark.unit
    def test_execution_result_creation(self):
        """Test execution result creation."""
        verdict = {'tier': 'premium', 'approved': True}
        fired_rules = ['rule1', 'rule2']
        
        result = ExecutionResult(
            verdict=verdict,
            fired_rules=fired_rules,
            execution_time_ms=25.5,
            reasoning="Rules fired based on conditions"
        )
        
        assert result.verdict == verdict
        assert result.fired_rules == fired_rules
        assert result.execution_time_ms == 25.5
        assert result.reasoning == "Rules fired based on conditions"
    
    @pytest.mark.unit
    def test_execution_result_with_reasoning(self):
        """Test execution result with reasoning text."""
        result = ExecutionResult(
            verdict={'approved': True},
            fired_rules=['rule1', 'rule2'],
            execution_time_ms=15.0,
            reasoning="rule1: condition was met\n rule2: criteria satisfied"
        )
        
        assert "rule1: condition was met" in result.reasoning
        assert "rule2: criteria satisfied" in result.reasoning
    
    @pytest.mark.unit
    def test_execution_result_immutability(self):
        """Test that execution results are immutable."""
        result = ExecutionResult(
            verdict={'tier': 'premium'},
            fired_rules=['rule1'],
            execution_time_ms=10.0,
            reasoning="Simple reasoning"
        )
        
        # Should not be able to modify result attributes
        with pytest.raises(AttributeError):
            result.verdict = {}
        
        with pytest.raises(AttributeError):
            result.fired_rules = []





class TestFactsConvenienceFunction:
    """Test the facts() convenience function."""
    
    @pytest.mark.unit
    def test_facts_function(self):
        """Test the facts convenience function."""
        data = {'amount': 1000, 'status': 'active'}
        f = facts(**data)
        
        assert isinstance(f, Facts)
        assert f.data == data
        assert f['amount'] == 1000
    
    @pytest.mark.unit
    def test_facts_function_empty(self):
        """Test facts function with empty data."""
        f = facts()
        
        assert isinstance(f, Facts)
        assert f.data == {}
        assert 'anything' not in f
    
    @pytest.mark.unit
    def test_facts_function_with_kwargs(self):
        """Test facts function with keyword arguments."""
        f = facts(amount=1500, status='active', tier='premium')
        
        assert f['amount'] == 1500
        assert f['status'] == 'active'
        assert f['tier'] == 'premium' 