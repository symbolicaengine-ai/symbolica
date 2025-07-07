"""
Unit Tests for Internal Condition Evaluator
===========================================

Tests for the ComprehensiveConditionEvaluator and related functionality.
"""

import pytest
from typing import Dict, Any

from symbolica.core import condition, ExecutionContext, facts, EvaluationError
from symbolica._internal.evaluator import (
    ComprehensiveConditionEvaluator, create_evaluator
)


class TestComprehensiveConditionEvaluator:
    """Test the comprehensive condition evaluator."""
    
    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return ComprehensiveConditionEvaluator()
    
    @pytest.fixture
    def context(self, sample_facts):
        """Create execution context."""
        return ExecutionContext(facts=facts(sample_facts))

    @pytest.mark.unit
    def test_simple_string_expressions(self, evaluator, context):
        """Test simple string-based expressions."""
        # Arithmetic comparisons
        assert evaluator.evaluate(condition("amount > 1000"), context) is True
        assert evaluator.evaluate(condition("amount < 1000"), context) is False
        assert evaluator.evaluate(condition("amount == 1500"), context) is True
        assert evaluator.evaluate(condition("amount != 2000"), context) is True
        
        # String comparisons
        assert evaluator.evaluate(condition("status == 'active'"), context) is True
        assert evaluator.evaluate(condition("status != 'inactive'"), context) is True
        
        # Membership tests
        assert evaluator.evaluate(condition("country in ['US', 'CA']"), context) is True
        assert evaluator.evaluate(condition("country not in ['UK', 'DE']"), context) is True
    
    @pytest.mark.unit
    def test_boolean_operators(self, evaluator, context):
        """Test boolean operators (and, or, not)."""
        # AND operator
        assert evaluator.evaluate(
            condition("amount > 1000 and status == 'active'"), context
        ) is True
        assert evaluator.evaluate(
            condition("amount > 2000 and status == 'active'"), context
        ) is False
        
        # OR operator
        assert evaluator.evaluate(
            condition("amount > 2000 or status == 'active'"), context
        ) is True
        assert evaluator.evaluate(
            condition("amount > 2000 or status == 'inactive'"), context
        ) is False
        
        # NOT operator
        assert evaluator.evaluate(
            condition("not status == 'inactive'"), context
        ) is True
        assert evaluator.evaluate(
            condition("not amount > 1000"), context
        ) is False
    
    @pytest.mark.unit
    def test_structured_yaml_expressions(self, evaluator, context):
        """Test structured YAML expressions."""
        # ALL combinator
        all_condition = condition({
            'all': ['amount > 1000', 'status == "active"', 'risk_score < 50']
        })
        assert evaluator.evaluate(all_condition, context) is True
        
        # ANY combinator
        any_condition = condition({
            'any': ['amount > 5000', 'user_type == "premium"', 'age > 65']
        })
        assert evaluator.evaluate(any_condition, context) is True
        
        # NOT combinator
        not_condition = condition({
            'not': 'status == "inactive"'
        })
        assert evaluator.evaluate(not_condition, context) is True
    
    @pytest.mark.unit
    def test_nested_structured_expressions(self, evaluator, context):
        """Test deeply nested structured expressions."""
        nested_condition = condition({
            'any': [
                {
                    'all': ['amount > 1000', 'status == "active"']
                },
                {
                    'all': ['user_type == "premium"', 'account_balance > 10000']
                }
            ]
        })
        assert evaluator.evaluate(nested_condition, context) is True
        
        complex_nested = condition({
            'all': [
                'amount > 500',
                {
                    'any': [
                        'status == "active"',
                        {
                            'all': ['user_type == "premium"', 'risk_score < 30']
                        }
                    ]
                }
            ]
        })
        assert evaluator.evaluate(complex_nested, context) is True
    
    @pytest.mark.unit
    def test_arithmetic_expressions(self, evaluator):
        """Test arithmetic expressions."""
        arithmetic_facts = facts({
            'a': 10,
            'b': 5,
            'c': 2.5,
            'd': 100
        })
        context = ExecutionContext(facts=arithmetic_facts)
        
        # Basic arithmetic
        assert evaluator.evaluate(condition("a + b == 15"), context) is True
        assert evaluator.evaluate(condition("a - b == 5"), context) is True
        assert evaluator.evaluate(condition("a * b == 50"), context) is True
        assert evaluator.evaluate(condition("a / b == 2"), context) is True
        assert evaluator.evaluate(condition("a % 3 == 1"), context) is True
        assert evaluator.evaluate(condition("a ** 2 == 100"), context) is True
        
        # Mixed types
        assert evaluator.evaluate(condition("a > c"), context) is True
        assert evaluator.evaluate(condition("c * 4 == a"), context) is True
    
    @pytest.mark.unit
    def test_string_functions(self, evaluator):
        """Test string functions."""
        string_facts = facts({
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'description': 'A premium customer with excellent credit'
        })
        context = ExecutionContext(facts=string_facts)
        
        # String functions
        assert evaluator.evaluate(
            condition("name.startswith('John')"), context
        ) is True
        assert evaluator.evaluate(
            condition("email.endswith('.com')"), context
        ) is True
        assert evaluator.evaluate(
            condition("'premium' in description"), context
        ) is True
        assert evaluator.evaluate(
            condition("len(name) > 5"), context
        ) is True
    
    @pytest.mark.unit
    def test_null_checks(self, evaluator):
        """Test null/None value handling."""
        null_facts = facts({
            'amount': 1000,
            'optional_field': None,
            'empty_string': '',
            'zero_value': 0
        })
        context = ExecutionContext(facts=null_facts)
        
        # Null checks
        assert evaluator.evaluate(
            condition("optional_field is None"), context
        ) is True
        assert evaluator.evaluate(
            condition("amount is not None"), context
        ) is True
        
        # Empty vs null
        assert evaluator.evaluate(
            condition("empty_string == ''"), context
        ) is True
        assert evaluator.evaluate(
            condition("zero_value == 0"), context
        ) is True
    
    @pytest.mark.unit
    def test_field_extraction(self, evaluator):
        """Test field extraction from expressions."""
        # Simple field extraction
        fields = evaluator.extract_fields(condition("amount > 1000"))
        assert 'amount' in fields
        
        # Multiple fields
        fields = evaluator.extract_fields(
            condition("amount > 1000 and status == 'active'")
        )
        assert 'amount' in fields
        assert 'status' in fields
        
        # Structured expression fields
        fields = evaluator.extract_fields(condition({
            'all': ['user_type == "premium"', 'risk_score < 50']
        }))
        assert 'user_type' in fields
        assert 'risk_score' in fields
    
    @pytest.mark.unit
    def test_caching(self, evaluator, context):
        """Test expression caching."""
        expr = condition("amount > 1000 and status == 'active'")
        
        # First evaluation
        result1 = evaluator.evaluate(expr, context)
        
        # Second evaluation should use cache
        result2 = evaluator.evaluate(expr, context)
        
        assert result1 == result2 is True
        
        # Cache should be content-based
        expr_same_content = condition("amount > 1000 and status == 'active'")
        result3 = evaluator.evaluate(expr_same_content, context)
        assert result3 == result1
    
    @pytest.mark.unit
    def test_security_limits(self, evaluator):
        """Test security limits for recursion and function calls."""
        # Deep recursion should be limited
        deep_nested = {'all': []}
        current = deep_nested['all']
        for i in range(100):  # Exceed max recursion depth
            nested = {'all': [f'field_{i} > {i}']}
            current.append(nested)
            current = nested['all']
        
        context = ExecutionContext(facts=facts({'field_1': 2}))
        
        with pytest.raises(EvaluationError, match="recursion depth"):
            evaluator.evaluate(condition(deep_nested), context)
    
    @pytest.mark.unit
    def test_error_handling(self, evaluator):
        """Test error handling for invalid expressions."""
        context = ExecutionContext(facts=facts({'amount': 1000}))
        
        # Division by zero
        with pytest.raises(EvaluationError):
            evaluator.evaluate(condition("amount / 0 > 100"), context)
        
        # Undefined field
        with pytest.raises(EvaluationError):
            evaluator.evaluate(condition("undefined_field > 500"), context)
        
        # Invalid syntax
        with pytest.raises(EvaluationError):
            evaluator.evaluate(condition("amount >"), context)
        
        # Type errors
        string_facts = facts({'amount': 'not_a_number'})
        string_context = ExecutionContext(facts=string_facts)
        with pytest.raises(EvaluationError):
            evaluator.evaluate(condition("amount + 100 > 1000"), string_context)
    
    @pytest.mark.unit
    def test_comparison_operators(self, evaluator):
        """Test all comparison operators."""
        test_facts = facts({
            'num': 42,
            'str': 'hello',
            'list': [1, 2, 3],
            'dict': {'key': 'value'}
        })
        context = ExecutionContext(facts=test_facts)
        
        # Numeric comparisons
        assert evaluator.evaluate(condition("num == 42"), context) is True
        assert evaluator.evaluate(condition("num != 41"), context) is True
        assert evaluator.evaluate(condition("num > 40"), context) is True
        assert evaluator.evaluate(condition("num >= 42"), context) is True
        assert evaluator.evaluate(condition("num < 50"), context) is True
        assert evaluator.evaluate(condition("num <= 42"), context) is True
        
        # String comparisons
        assert evaluator.evaluate(condition("str == 'hello'"), context) is True
        assert evaluator.evaluate(condition("str != 'world'"), context) is True
        
        # Container membership
        assert evaluator.evaluate(condition("2 in list"), context) is True
        assert evaluator.evaluate(condition("4 not in list"), context) is True
        assert evaluator.evaluate(condition("'key' in dict"), context) is True
    
    @pytest.mark.unit
    def test_performance_with_large_expressions(self, evaluator):
        """Test performance with large expressions."""
        # Create a large expression with many conditions
        large_facts = facts({f'field_{i}': i for i in range(100)})
        context = ExecutionContext(facts=large_facts)
        
        # Large AND chain
        conditions = [f'field_{i} == {i}' for i in range(50)]
        large_condition = condition(' and '.join(conditions))
        
        # Should complete without timeout
        result = evaluator.evaluate(large_condition, context)
        assert result is True


class TestEvaluatorFactory:
    """Test evaluator factory function."""
    
    @pytest.mark.unit
    def test_create_evaluator(self):
        """Test evaluator factory function."""
        evaluator = create_evaluator()
        assert isinstance(evaluator, ComprehensiveConditionEvaluator)
    
    @pytest.mark.unit
    def test_create_evaluator_with_params(self):
        """Test evaluator factory with custom parameters."""
        evaluator = create_evaluator(
            max_recursion_depth=25,
            max_function_calls=50
        )
        assert isinstance(evaluator, ComprehensiveConditionEvaluator)
        assert evaluator._max_recursion_depth == 25
        assert evaluator._max_function_calls == 50 