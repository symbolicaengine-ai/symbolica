"""
Unit tests for custom functions feature.
"""

import pytest
import time
from typing import Any

from symbolica import Engine, facts
from symbolica.core.exceptions import ValidationError, EvaluationError
from symbolica._internal.evaluation.evaluator import ASTEvaluator


class TestCustomFunctionRegistration:
    """Test custom function registration and management."""
    
    def test_register_lambda_function(self):
        """Test registering safe lambda functions."""
        engine = Engine()
        
        # Test simple lambda
        engine.register_function("double", lambda x: x * 2)
        functions = engine.list_functions()
        assert "double" in functions
        assert "lambda" in functions["double"]
        
        # Test complex lambda
        engine.register_function("risk_score", lambda score: 
            "low" if score > 750 else "high" if score < 600 else "medium")
        functions = engine.list_functions()
        assert "risk_score" in functions
    
    def test_register_unsafe_function_rejected_by_default(self):
        """Test that non-lambda functions are rejected by default."""
        engine = Engine()
        
        def unsafe_func(x):
            return x * 2
        
        with pytest.raises(ValidationError, match="Function 'unsafe_func' is not a lambda"):
            engine.register_function("unsafe_func", unsafe_func)
    
    def test_register_unsafe_function_with_explicit_flag(self):
        """Test registering unsafe functions with explicit allow_unsafe=True."""
        engine = Engine()
        
        def complex_function(x, y, z):
            result = 0
            for i in range(x):
                result += y * z
            return result
        
        engine.register_function("complex_func", complex_function, allow_unsafe=True)
        functions = engine.list_functions()
        assert "complex_func" in functions
        assert "complex_function" in functions["complex_func"]
    
    def test_function_name_validation(self):
        """Test function name validation."""
        engine = Engine()
        
        # Invalid identifier
        with pytest.raises(ValidationError, match="is not a valid identifier"):
            engine.register_function("invalid-name", lambda x: x)
        
        # Reserved word
        with pytest.raises(ValidationError, match="is reserved"):
            engine.register_function("len", lambda x: x)
        
        # Non-callable - test with allow_unsafe to bypass lambda check
        with pytest.raises(ValidationError, match="must be callable"):
            engine.register_function("not_func", "not a function", allow_unsafe=True)
    
    def test_unregister_function(self):
        """Test unregistering custom functions."""
        engine = Engine()
        
        engine.register_function("test_func", lambda x: x)
        assert "test_func" in engine.list_functions()
        
        engine.unregister_function("test_func")
        assert "test_func" not in engine.list_functions()
        
        # Unregistering non-existent function should not error
        engine.unregister_function("non_existent")
    
    def test_list_functions_includes_builtin_and_custom(self):
        """Test that list_functions includes both built-in and custom functions."""
        engine = Engine()
        
        functions = engine.list_functions()
        # Check built-ins
        assert "len" in functions
        assert "sum" in functions
        assert "abs" in functions
        
        # Add custom function
        engine.register_function("custom", lambda x: x)
        functions = engine.list_functions()
        assert "custom" in functions
        assert "len" in functions  # Still there


class TestCustomFunctionExecution:
    """Test custom function execution in rules."""
    
    def test_simple_custom_function_execution(self):
        """Test basic custom function execution."""
        yaml_rules = """
rules:
  - id: test_rule
    condition: "double(value) > 10"
    actions:
      result: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        engine.register_function("double", lambda x: x * 2)
        
        result = engine.reason(facts(value=6))
        assert result.verdict == {"result": True}
        assert "test_rule" in result.fired_rules
    
    def test_multiple_custom_functions(self):
        """Test multiple custom functions in same condition."""
        yaml_rules = """
rules:
  - id: complex_rule
    condition: "add(value1, value2) == multiply(value3, 2)"
    actions:
      match: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        engine.register_function("add", lambda x, y: x + y)
        engine.register_function("multiply", lambda x, y: x * y)
        
        result = engine.reason(facts(value1=5, value2=3, value3=4))
        assert result.verdict == {"match": True}
    
    def test_custom_function_with_builtin_functions(self):
        """Test custom functions working alongside built-in functions."""
        yaml_rules = """
rules:
  - id: mixed_rule
    condition: "len(items) > 0 and custom_sum(items) > threshold"
    actions:
      processed: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        engine.register_function("custom_sum", lambda lst: sum(lst) * 2)
        
        result = engine.reason(facts(items=[1, 2, 3], threshold=10))
        assert result.verdict == {"processed": True}
    
    def test_custom_function_return_types(self):
        """Test custom functions returning different types."""
        yaml_rules = """
rules:
  - id: string_func
    condition: "get_grade(score) == 'A'"
    actions:
      grade_a: true
      
  - id: bool_func
    condition: "is_valid(data) == True"
    actions:
      valid: true
      
  - id: number_func
    condition: "calculate_fee(amount) < 100"
    actions:
      low_fee: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        engine.register_function("get_grade", lambda score: "A" if score >= 90 else "B" if score >= 80 else "C")
        engine.register_function("is_valid", lambda data: data is not None and len(str(data)) > 0)
        engine.register_function("calculate_fee", lambda amount: amount * 0.05)
        
        result = engine.reason(facts(score=95, data="test", amount=1000))
        # calculate_fee(1000) = 50, which is < 100, so low_fee should be True
        assert result.verdict == {"grade_a": True, "valid": True, "low_fee": True}
        assert "string_func" in result.fired_rules
        assert "bool_func" in result.fired_rules
        assert "number_func" in result.fired_rules


class TestCustomFunctionErrorHandling:
    """Test error handling in custom functions."""
    
    def test_function_error_isolation(self):
        """Test that function errors don't crash the engine."""
        yaml_rules = """
rules:
  - id: error_rule
    condition: "divide(value, 0) > 5"
    actions:
      should_not_fire: true
      
  - id: good_rule
    condition: "value > 5"
    actions:
      should_fire: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        engine.register_function("divide", lambda x, y: x / y)
        
        result = engine.reason(facts(value=10))
        # Error rule should not fire due to division by zero
        # Good rule should still fire
        assert result.verdict == {"should_fire": True}
        assert "good_rule" in result.fired_rules
        assert "error_rule" not in result.fired_rules
    
    def test_function_type_errors(self):
        """Test handling of type errors in custom functions."""
        yaml_rules = """
rules:
  - id: type_error_rule
    condition: "add_numbers(value1, value2) > 0"
    actions:
      result: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        engine.register_function("add_numbers", lambda x, y: x + y)
        
        # Should not crash with type error
        result = engine.reason(facts(value1="string", value2="another"))
        assert result.verdict == {}  # No rules should fire
        assert result.fired_rules == []
    
    def test_function_with_none_values(self):
        """Test custom functions handling None values gracefully."""
        yaml_rules = """
rules:
  - id: null_safe_rule
    condition: "safe_operation(value) != None"
    actions:
      processed: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        engine.register_function("safe_operation", lambda x: x * 2 if x is not None else None)
        
        # Test with None
        result1 = engine.reason(facts(value=None))
        assert result1.verdict == {}
        
        # Test with valid value
        result2 = engine.reason(facts(value=5))
        assert result2.verdict == {"processed": True}


class TestCustomFunctionSafety:
    """Test safety controls for custom functions."""
    
    def test_lambda_detection_accuracy(self):
        """Test accurate detection of lambda vs regular functions."""
        engine = Engine()
        
        # Lambda should be accepted
        lambda_func = lambda x: x * 2
        engine.register_function("lambda_func", lambda_func)
        
        # Regular function should be rejected
        def regular_func(x):
            return x * 2
        
        with pytest.raises(ValidationError, match="is not a lambda"):
            engine.register_function("regular_func", regular_func)
        
        # Built-in function should be rejected
        with pytest.raises(ValidationError, match="is not a lambda"):
            engine.register_function("builtin_func", abs)
    
    def test_lambda_with_complex_expressions(self):
        """Test that complex lambda expressions are still considered safe."""
        engine = Engine()
        
        # Complex lambda expressions should work
        complex_lambda = lambda x, y, z: (x + y) * z if z > 0 else x - y
        engine.register_function("complex_calc", complex_lambda)
        
        nested_lambda = lambda data: sum(item['value'] for item in data if item.get('active', False))
        engine.register_function("nested_calc", nested_lambda)
        
        functions = engine.list_functions()
        assert "complex_calc" in functions
        assert "nested_calc" in functions
    
    def test_method_references_rejected(self):
        """Test that method references are rejected for safety."""
        engine = Engine()
        
        class TestClass:
            def method(self, x):
                return x * 2
        
        obj = TestClass()
        
        with pytest.raises(ValidationError, match="is not a lambda"):
            engine.register_function("method_ref", obj.method)


class TestCustomFunctionFieldExtraction:
    """Test that custom functions don't interfere with field extraction."""
    
    def test_function_names_excluded_from_fields(self):
        """Test that function names are not treated as fields."""
        evaluator = ASTEvaluator()
        evaluator.register_function("custom_func", lambda x: x)
        
        fields = evaluator.extract_fields("custom_func(real_field) > threshold")
        assert "custom_func" not in fields
        assert "real_field" in fields
        assert "threshold" in fields
    
    def test_complex_expression_field_extraction(self):
        """Test field extraction with complex custom function usage."""
        evaluator = ASTEvaluator()
        evaluator.register_function("risk_calc", lambda a, b, c: a + b + c)
        evaluator.register_function("threshold_func", lambda x: x * 0.1)
        
        fields = evaluator.extract_fields(
            "risk_calc(credit_score, income, debt) > threshold_func(base_threshold)"
        )
        
        assert "risk_calc" not in fields
        assert "threshold_func" not in fields
        assert "credit_score" in fields
        assert "income" in fields
        assert "debt" in fields
        assert "base_threshold" in fields


class TestCustomFunctionPerformance:
    """Test performance aspects of custom functions."""
    
    def test_custom_function_performance_impact(self):
        """Test that custom functions don't significantly impact performance."""
        yaml_rules = """
rules:
  - id: perf_rule_1
    condition: "fast_calc(value) > 10"
    actions:
      result1: true
      
  - id: perf_rule_2
    condition: "value > 5 and fast_calc(value) < 100"
    actions:
      result2: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        engine.register_function("fast_calc", lambda x: x * 2 + 1)
        
        # Measure execution time
        start_time = time.perf_counter()
        for _ in range(100):
            result = engine.reason(facts(value=15))
        end_time = time.perf_counter()
        
        avg_time_ms = (end_time - start_time) * 1000 / 100
        
        # Should complete quickly (less than 1ms average)
        assert avg_time_ms < 1.0
        assert result.verdict == {"result1": True, "result2": True}
    
    def test_function_call_efficiency(self):
        """Test that repeated function calls are efficient."""
        evaluator = ASTEvaluator()
        evaluator.register_function("test_func", lambda x: x * x)
        
        # Create a context for testing
        from symbolica.core.models import Facts, ExecutionContext
        facts_obj = Facts({"value": 5})
        context = ExecutionContext(original_facts=facts_obj, enriched_facts={}, fired_rules=[])
        
        # Test multiple evaluations
        start_time = time.perf_counter()
        for _ in range(1000):
            result = evaluator.evaluate("test_func(value) > 20", context)
        end_time = time.perf_counter()
        
        total_time_ms = (end_time - start_time) * 1000
        assert total_time_ms < 100  # Should complete 1000 evals in under 100ms


class TestCustomFunctionTracing:
    """Test tracing and reasoning with custom functions."""
    
    def test_custom_function_in_reasoning_trace(self):
        """Test that custom functions appear properly in reasoning traces."""
        yaml_rules = """
rules:
  - id: trace_rule
    condition: "calculate_score(base, multiplier) >= target"
    actions:
      qualified: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        engine.register_function("calculate_score", lambda base, mult: base * mult)
        
        result = engine.reason(facts(base=10, multiplier=3, target=25))
        
        # Check that function call appears in reasoning
        assert "calculate_score(base(10), multiplier(3))" in result.reasoning
        assert "qualified" in result.verdict
        assert result.verdict["qualified"] is True
    
    def test_complex_condition_tracing(self):
        """Test tracing of complex conditions with custom functions."""
        yaml_rules = """
rules:
  - id: complex_trace_rule
    condition: "risk_score(credit) == 'low' and income_check(salary) == True"
    actions:
      approved: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        engine.register_function("risk_score", lambda credit: "low" if credit > 700 else "high")
        engine.register_function("income_check", lambda salary: salary > 50000)
        
        result = engine.reason(facts(credit=750, salary=60000))
        
        # Should show both function calls in reasoning
        reasoning = result.reasoning
        assert "risk_score(credit(750))" in reasoning
        assert "income_check(salary(60000))" in reasoning
        assert "approved" in result.verdict


class TestCustomFunctionEdgeCases:
    """Test edge cases and corner scenarios."""
    
    def test_function_with_variable_arguments(self):
        """Test functions that accept variable arguments."""
        engine = Engine()
        
        # Function with *args
        engine.register_function("sum_all", lambda *args: sum(args))
        
        yaml_rules = """
rules:
  - id: varargs_rule
    condition: "sum_all(a, b, c) > 10"
    actions:
      total_high: true
"""
        
        engine_with_rules = Engine.from_yaml(yaml_rules)
        engine_with_rules.register_function("sum_all", lambda *args: sum(args))
        
        result = engine_with_rules.reason(facts(a=2, b=3, c=6))
        assert result.verdict == {"total_high": True}
    
    def test_function_overwriting(self):
        """Test overwriting existing custom functions."""
        engine = Engine()
        
        # Register initial function
        engine.register_function("test_func", lambda x: x * 2)
        result1 = list(engine.list_functions().keys())
        assert "test_func" in result1
        
        # Overwrite with new function
        engine.register_function("test_func", lambda x: x * 3)
        result2 = list(engine.list_functions().keys())
        assert "test_func" in result2
        assert result1 == result2  # Same functions list
    
    def test_function_with_no_arguments(self):
        """Test functions that take no arguments."""
        engine = Engine()
        
        engine.register_function("get_constant", lambda: 42)
        
        yaml_rules = """
rules:
  - id: constant_rule
    condition: "value > get_constant()"
    actions:
      above_constant: true
"""
        
        engine_with_rules = Engine.from_yaml(yaml_rules)
        engine_with_rules.register_function("get_constant", lambda: 42)
        
        result = engine_with_rules.reason(facts(value=50))
        assert result.verdict == {"above_constant": True}
    
    def test_function_name_conflicts_with_fields(self):
        """Test handling when function names might conflict with field names."""
        yaml_rules = """
rules:
  - id: conflict_rule
    condition: "process(data) > data"
    actions:
      processed: true
"""
        
        engine = Engine.from_yaml(yaml_rules)
        engine.register_function("process", lambda x: x * 2)
        
        # 'data' is both a field and appears in function call
        result = engine.reason(facts(data=5))
        assert result.verdict == {"processed": True}
        
        # Verify field extraction works correctly
        fields = engine._evaluator.extract_fields("process(data) > data")
        assert "data" in fields
        assert "process" not in fields


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 