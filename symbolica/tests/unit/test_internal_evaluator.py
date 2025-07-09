"""
Unit Tests for Simplified AST Evaluator
=======================================

Tests for the simplified AST-based expression evaluator.
"""

import pytest
from typing import Dict, Any

from symbolica.core import ExecutionContext, facts, EvaluationError
from symbolica._internal.evaluator import ASTEvaluator


class TestASTEvaluator:
    """Test the simplified AST evaluator."""
    
    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return ASTEvaluator()
    
    @pytest.fixture
    def context(self, sample_facts):
        """Create execution context."""
        return ExecutionContext(
            original_facts=facts(**sample_facts),
            enriched_facts={},
            fired_rules=[]
        )

    @pytest.mark.unit
    def test_simple_comparisons(self, evaluator, context):
        """Test simple comparison expressions."""
        # Arithmetic comparisons
        assert evaluator.evaluate("amount > 1000", context) is True
        assert evaluator.evaluate("amount < 1000", context) is False
        assert evaluator.evaluate("amount == 1500", context) is True
        assert evaluator.evaluate("amount != 2000", context) is True
        assert evaluator.evaluate("amount >= 1500", context) is True
        assert evaluator.evaluate("amount <= 1500", context) is True
        
        # String comparisons
        assert evaluator.evaluate("status == 'active'", context) is True
        assert evaluator.evaluate("status != 'inactive'", context) is True
        
        # List membership
        assert evaluator.evaluate("country in ['US', 'CA']", context) is True
        assert evaluator.evaluate("country not in ['UK', 'DE']", context) is True
    
    @pytest.mark.unit
    def test_boolean_operators(self, evaluator, context):
        """Test boolean operators (and, or, not)."""
        # AND operator
        assert evaluator.evaluate("amount > 1000 and status == 'active'", context) is True
        assert evaluator.evaluate("amount > 2000 and status == 'active'", context) is False
        
        # OR operator
        assert evaluator.evaluate("amount > 2000 or status == 'active'", context) is True
        assert evaluator.evaluate("amount > 2000 or status == 'inactive'", context) is False
        
        # NOT operator
        assert evaluator.evaluate("not status == 'inactive'", context) is True
        assert evaluator.evaluate("not amount > 1000", context) is False
    
    @pytest.mark.unit
    def test_arithmetic_expressions(self, evaluator):
        """Test arithmetic expressions."""
        arithmetic_facts = facts(a=10, b=5, c=2.5, d=100)
        context = ExecutionContext(
            original_facts=arithmetic_facts,
            enriched_facts={},
            fired_rules=[]
        )
        
        # Basic arithmetic
        assert evaluator.evaluate("a + b == 15", context) is True
        assert evaluator.evaluate("a - b == 5", context) is True
        assert evaluator.evaluate("a * b == 50", context) is True
        assert evaluator.evaluate("a / b == 2", context) is True
        assert evaluator.evaluate("a % 3 == 1", context) is True
        
        # Mixed types
        assert evaluator.evaluate("a > c", context) is True
        assert evaluator.evaluate("c * 4 == a", context) is True
    
    @pytest.mark.unit
    def test_string_functions(self, evaluator):
        """Test string functions."""
        string_facts = facts(
            name='John Doe',
            email='john.doe@example.com',
            description='A premium customer with excellent credit'
        )
        context = ExecutionContext(
            original_facts=string_facts,
            enriched_facts={},
            fired_rules=[]
        )
        
        # String functions
        assert evaluator.evaluate("startswith(name, 'John')", context) is True
        assert evaluator.evaluate("endswith(email, '.com')", context) is True
        assert evaluator.evaluate("contains(description, 'premium')", context) is True
        assert evaluator.evaluate("len(name) > 5", context) is True
    
    @pytest.mark.unit
    def test_list_operations(self, evaluator):
        """Test list operations."""
        list_facts = facts(
            tags=['vip', 'loyalty', 'premium'],
            payment_history=[100, 95, 88, 92, 98],
            empty_list=[]
        )
        context = ExecutionContext(
            original_facts=list_facts,
            enriched_facts={},
            fired_rules=[]
        )
        
        # List membership
        assert evaluator.evaluate("'vip' in tags", context) is True
        assert evaluator.evaluate("'basic' not in tags", context) is True
        
        # List functions
        assert evaluator.evaluate("len(tags) == 3", context) is True
        assert evaluator.evaluate("len(payment_history) >= 5", context) is True
        assert evaluator.evaluate("sum(payment_history) > 400", context) is True
        assert evaluator.evaluate("len(empty_list) == 0", context) is True
    
    @pytest.mark.unit
    def test_null_checks(self, evaluator):
        """Test null/None value handling."""
        null_facts = facts(
            amount=1000,
            optional_field=None,
            empty_string='',
            zero_value=0,
            false_value=False
        )
        context = ExecutionContext(
            original_facts=null_facts,
            enriched_facts={},
            fired_rules=[]
        )
        
        # Null checks
        assert evaluator.evaluate("optional_field == None", context) is True
        assert evaluator.evaluate("amount != None", context) is True
        
        # Empty vs null
        assert evaluator.evaluate("empty_string == ''", context) is True
        assert evaluator.evaluate("zero_value == 0", context) is True
        assert evaluator.evaluate("false_value == False", context) is True
    
    @pytest.mark.unit
    def test_complex_expressions(self, evaluator, expression_test_facts):
        """Test complex expressions with multiple operations."""
        context = ExecutionContext(
            original_facts=facts(**expression_test_facts),
            enriched_facts={},
            fired_rules=[]
        )
        
        # Complex boolean logic
        complex_expr = "(amount > 1000 and status == 'active') or (user_type == 'premium' and account_balance > 3000)"
        assert evaluator.evaluate(complex_expr, context) is True
        
        # Arithmetic with comparisons
        calc_expr = "amount + account_balance > 6000"
        assert evaluator.evaluate(calc_expr, context) is True
        
        # Mixed operations
        mixed_expr = "len(tags) >= 2 and 'vip' in tags and amount > sum([100, 200, 300])"
        assert evaluator.evaluate(mixed_expr, context) is True
    
    @pytest.mark.unit
    def test_field_extraction(self, evaluator):
        """Test field extraction from expressions."""
        # Simple field extraction
        fields = evaluator.extract_fields("amount > 1000")
        assert 'amount' in fields
        
        # Multiple fields
        fields = evaluator.extract_fields("amount > 1000 and status == 'active'")
        assert 'amount' in fields
        assert 'status' in fields
        
        # Complex expressions
        fields = evaluator.extract_fields("user_type == 'premium' and account_balance > sum(payment_history)")
        assert 'user_type' in fields
        assert 'account_balance' in fields
        assert 'payment_history' in fields
    
    @pytest.mark.unit
    def test_caching(self, evaluator, context):
        """Test expression caching for performance."""
        expr = "amount > 1000 and status == 'active'"
        
        # First evaluation
        result1 = evaluator.evaluate(expr, context)
        
        # Second evaluation should use cache
        result2 = evaluator.evaluate(expr, context)
        
        assert result1 == result2 is True
        
        # Different expression should not use cache
        different_expr = "amount > 2000 and status == 'active'"
        result3 = evaluator.evaluate(different_expr, context)
        assert result3 is False  # Different result
    
    @pytest.mark.unit
    def test_error_handling(self, evaluator):
        """Test error handling for invalid expressions."""
        context = ExecutionContext(
            original_facts=facts(amount=1000),
            enriched_facts={},
            fired_rules=[]
        )
        
        # Division by zero
        with pytest.raises(EvaluationError):
            evaluator.evaluate("amount / 0 > 100", context)
        
        # Undefined field
        with pytest.raises(EvaluationError):
            evaluator.evaluate("undefined_field > 500", context)
        
        # Invalid syntax
        with pytest.raises(EvaluationError):
            evaluator.evaluate("amount >", context)
        
        # Type errors
        string_context = ExecutionContext(
            original_facts=facts(amount='not_a_number'),
            enriched_facts={},
            fired_rules=[]
        )
        with pytest.raises(EvaluationError):
            evaluator.evaluate("amount + 100 > 1000", string_context)
    
    @pytest.mark.unit
    def test_comparison_operators(self, evaluator):
        """Test all comparison operators."""
        test_facts = facts(
            num=42,
            str='hello',
            list=[1, 2, 3],
            dict={'key': 'value'}
        )
        context = ExecutionContext(
            original_facts=test_facts,
            enriched_facts={},
            fired_rules=[]
        )
        
        # Numeric comparisons
        assert evaluator.evaluate("num == 42", context) is True
        assert evaluator.evaluate("num != 41", context) is True
        assert evaluator.evaluate("num > 40", context) is True
        assert evaluator.evaluate("num >= 42", context) is True
        assert evaluator.evaluate("num < 50", context) is True
        assert evaluator.evaluate("num <= 42", context) is True
        
        # String comparisons
        assert evaluator.evaluate("str == 'hello'", context) is True
        assert evaluator.evaluate("str != 'world'", context) is True
        
        # Container membership
        assert evaluator.evaluate("2 in list", context) is True
        assert evaluator.evaluate("4 not in list", context) is True
    
    @pytest.mark.unit
    def test_parametrized_expressions(self, evaluator, context):
        """Test expressions with various parameter types."""
        test_cases = [
            ("amount > 1000", True),
            ("amount < 1000", False), 
            ("amount == 1500", True),
            ("status == 'active'", True),
            ("status != 'inactive'", True),
            ("amount > 1000 and status == 'active'", True),
            ("amount > 2000 or status == 'active'", True),
            ("not status == 'inactive'", True),
            ("country in ['US', 'CA']", True),
            ("country not in ['UK', 'DE']", True),
        ]
        
        for expr, expected in test_cases:
            result = evaluator.evaluate(expr, context)
            assert result == expected, f"Expression '{expr}' expected {expected}, got {result}"
    
    @pytest.mark.unit
    def test_performance_with_large_expressions(self, evaluator):
        """Test performance with moderately complex expressions."""
        # Create facts for testing
        large_facts = facts(**{f'field_{i}': i for i in range(50)})
        context = ExecutionContext(
            original_facts=large_facts,
            enriched_facts={},
            fired_rules=[]
        )
        
        # Large AND chain
        conditions = [f'field_{i} == {i}' for i in range(25)]
        large_condition = ' and '.join(conditions)
        
        # Should complete without timeout
        result = evaluator.evaluate(large_condition, context)
        assert result is True


class TestEvaluatorFactory:
    """Test evaluator factory function."""
    
    @pytest.mark.unit
    def test_create_evaluator(self):
        """Test evaluator direct instantiation."""
        evaluator = ASTEvaluator()
        assert isinstance(evaluator, ASTEvaluator)
    
    @pytest.mark.unit
    def test_evaluator_methods(self):
        """Test that evaluator has required methods."""
        evaluator = ASTEvaluator()
        
        assert hasattr(evaluator, 'evaluate')
        assert hasattr(evaluator, 'extract_fields')
        assert callable(evaluator.evaluate)
        assert callable(evaluator.extract_fields)


class TestExpressionTestCases:
    """Test expression evaluation using parametrized test cases from conftest."""
    
    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return ASTEvaluator()
    
    @pytest.mark.unit 
    def test_expression_cases(self, evaluator, expression_test_facts):
        """Test all expression cases from conftest."""
        from symbolica.tests.conftest import EXPRESSION_TEST_CASES
        
        context = ExecutionContext(
            original_facts=facts(**expression_test_facts),
            enriched_facts={},
            fired_rules=[]
        )
        
        for case in EXPRESSION_TEST_CASES:
            expr = case['expr']
            expected = case['expected']
            
            try:
                result = evaluator.evaluate(expr, context)
                assert result == expected, f"Expression '{expr}' expected {expected}, got {result}"
            except Exception as e:
                pytest.fail(f"Expression '{expr}' failed with error: {e}")


class TestErrorTestCases:
    """Test error handling using error test cases from conftest."""
    
    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return ASTEvaluator()
    
    @pytest.mark.unit
    def test_error_cases(self, evaluator):
        """Test error cases from conftest."""
        from symbolica.tests.conftest import ERROR_TEST_CASES
        
        for case in ERROR_TEST_CASES:
            name = case['name']
            test_facts = facts(**case['facts'])
            condition = case['condition']
            
            context = ExecutionContext(
                original_facts=test_facts,
                enriched_facts={},
                fired_rules=[]
            )
            
            with pytest.raises(EvaluationError, match=".*"):
                evaluator.evaluate(condition, context) 