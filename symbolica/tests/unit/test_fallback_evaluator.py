"""
Tests for FallbackEvaluator
============================

Tests the prompt() wrapper functionality that provides graceful degradation
from structured evaluation to LLM fallback.
"""

import pytest
from unittest.mock import Mock, MagicMock

from symbolica.core.engine import Engine
from symbolica.core.models import Facts, Rule
from symbolica.core.exceptions import EvaluationError
from symbolica.llm.fallback_evaluator import FallbackEvaluator, FallbackResult


class MockLLMClient:
    """Mock LLM client for testing."""
    
    def __init__(self):
        # Mock the OpenAI client interface
        self.chat = Mock()
        self.chat.completions = Mock()
        self.chat.completions.create = self._mock_create
    
    def _mock_create(self, **kwargs):
        # Simulate successful LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "true"
        mock_response.model = "gpt-3.5-turbo"
        return mock_response

# Set the module to make it look like an OpenAI client
MockLLMClient.__module__ = 'openai'


class TestFallbackEvaluator:
    """Test FallbackEvaluator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock structured evaluator
        self.mock_structured_evaluator = Mock()
        self.mock_structured_evaluator.evaluate.return_value = True
        self.mock_structured_evaluator.extract_fields.return_value = ["credit_score"]
        
        # Mock prompt evaluator
        self.mock_prompt_evaluator = Mock()
        self.mock_prompt_evaluator.evaluate_prompt.return_value = True
        
        # Create fallback evaluator
        self.fallback = FallbackEvaluator(
            self.mock_structured_evaluator,
            self.mock_prompt_evaluator
        )

    def test_structured_evaluation_success(self):
        """Test successful structured evaluation (no fallback needed)."""
        # Complete data should trigger structured evaluation
        facts = {"credit_score": 750}
        
        result = self.fallback.prompt(
            "credit_score > 700",
            return_type="bool",
            context_facts=facts
        )
        
        assert result.value is True
        assert result.method_used == "structured"
        assert result.structured_error is None
        assert result.execution_time_ms > 0
        
        # Verify structured evaluator was called
        self.mock_structured_evaluator.evaluate.assert_called_once()
        # Verify LLM was not called
        self.mock_prompt_evaluator.evaluate_prompt.assert_not_called()

    def test_llm_fallback_on_missing_fields(self):
        """Test LLM fallback when required fields are missing."""
        # Mock structured evaluator to raise error for missing fields
        self.mock_structured_evaluator.evaluate.side_effect = EvaluationError("Missing required fields: ['credit_score']")
        
        facts = {"annual_income": 80000}  # credit_score missing
        
        result = self.fallback.prompt(
            "credit_score > 700",
            return_type="bool", 
            context_facts=facts
        )
        
        assert result.value is True
        assert result.method_used == "llm"
        assert "Missing required fields" in result.structured_error
        assert result.llm_reasoning is not None
        
        # Verify both evaluators were called
        self.mock_structured_evaluator.evaluate.assert_called_once()
        self.mock_prompt_evaluator.evaluate_prompt.assert_called_once()

    def test_llm_fallback_on_evaluation_error(self):
        """Test LLM fallback when structured evaluation fails."""
        # Mock structured evaluator to fail
        self.mock_structured_evaluator.evaluate.side_effect = Exception("Parse error")
        
        facts = {"credit_score": 750}
        
        result = self.fallback.prompt(
            "invalid_syntax >>>",
            return_type="bool",
            context_facts=facts
        )
        
        assert result.value is True
        assert result.method_used == "llm"
        assert "Parse error" in result.structured_error

    def test_type_conversion(self):
        """Test type conversion for different return types."""
        facts = {"score": 85}
        
        # Mock extract_fields to return the field that exists
        self.mock_structured_evaluator.extract_fields.return_value = ["score"]
        
        # Test bool conversion
        result = self.fallback.prompt("score > 80", "bool", context_facts=facts)
        assert isinstance(result.value, bool)
        
        # Test int conversion (mock to return string)
        self.mock_structured_evaluator.evaluate.return_value = "85"
        result = self.fallback.prompt("score", "int", context_facts=facts)
        assert result.value == 85
        assert isinstance(result.value, int)

    def test_default_fallback_on_total_failure(self):
        """Test default value when both structured and LLM fail."""
        # Both evaluators fail
        self.mock_structured_evaluator.evaluate.side_effect = Exception("Structured failed")
        self.mock_prompt_evaluator.evaluate_prompt.side_effect = Exception("LLM failed")
        
        result = self.fallback.prompt(
            "some condition",
            return_type="bool",
            context_facts={}
        )
        
        assert result.value is False  # Default bool value
        assert result.method_used == "default"
        assert "Structured failed" in result.structured_error
        assert "LLM failed" in result.llm_reasoning

    def test_statistics_tracking(self):
        """Test fallback statistics are tracked correctly."""
        facts = {"credit_score": 750}
        
        # Reset stats
        self.fallback.reset_stats()
        
        # Successful structured evaluation
        self.fallback.prompt("credit_score > 700", "bool", context_facts=facts)
        
        # Failed structured, successful LLM
        self.mock_structured_evaluator.evaluate.side_effect = Exception("Error")
        self.fallback.prompt("credit_score > 700", "bool", context_facts=facts)
        
        stats = self.fallback.get_fallback_stats()
        
        assert stats['total_calls'] == 2
        assert stats['structured_success'] == 1
        assert stats['llm_fallback'] == 1
        assert stats['structured_success_rate'] == 0.5
        assert stats['llm_fallback_rate'] == 0.5

    def test_enhanced_prompt_building(self):
        """Test that enhanced prompts are built correctly for LLM."""
        # Force LLM fallback
        self.mock_structured_evaluator.evaluate.side_effect = Exception("Error")
        
        facts = {
            "credit_score": 750,
            "annual_income": None,  # Missing data
            "customer_type": "premium"
        }
        
        self.fallback.prompt(
            "customer has good credit",
            return_type="bool",
            context_facts=facts
        )
        
        # Verify prompt evaluator was called with enhanced prompt
        call_args = self.mock_prompt_evaluator.evaluate_prompt.call_args
        prompt_args = call_args[0][0]
        
        # Enhanced prompt should contain available and missing data info
        enhanced_prompt = prompt_args[0]
        assert "Available data:" in enhanced_prompt
        assert "credit_score: 750" in enhanced_prompt
        assert "customer_type: premium" in enhanced_prompt
        assert "Missing/incomplete data:" in enhanced_prompt
        assert "annual_income" in enhanced_prompt

    def test_empty_context_facts(self):
        """Test handling of empty or None context facts."""
        # Mock extract_fields to return no required fields
        self.mock_structured_evaluator.extract_fields.return_value = []
        
        # Should not crash with empty facts
        result = self.fallback.prompt(
            "some condition",
            return_type="bool",
            context_facts=None
        )
        
        assert result.value is True
        assert result.method_used == "structured"
        
        # Test with empty dict
        result = self.fallback.prompt(
            "some condition", 
            return_type="bool",
            context_facts={}
        )
        
        assert result.value is True

    def test_rule_id_propagation(self):
        """Test that rule_id is properly passed through to LLM evaluator."""
        # Force LLM fallback
        self.mock_structured_evaluator.evaluate.side_effect = Exception("Error")
        
        self.fallback.prompt(
            "some condition",
            return_type="bool",
            context_facts={},
            rule_id="test_rule_123"
        )
        
        # Verify rule_id was passed to prompt evaluator
        call_args = self.mock_prompt_evaluator.evaluate_prompt.call_args
        assert call_args[1]['rule_id'] == "test_rule_123"


class TestFallbackResult:
    """Test FallbackResult data structure."""
    
    def test_fallback_result_creation(self):
        """Test creating FallbackResult with different parameters."""
        result = FallbackResult(
            value=True,
            method_used="structured",
            execution_time_ms=1.5
        )
        
        assert result.value is True
        assert result.method_used == "structured"
        assert result.structured_error is None
        assert result.llm_reasoning is None
        assert result.execution_time_ms == 1.5

    def test_fallback_result_with_errors(self):
        """Test FallbackResult with error information."""
        result = FallbackResult(
            value=False,
            method_used="llm",
            structured_error="Missing field: credit_score",
            llm_reasoning="Customer data insufficient for approval",
            execution_time_ms=250.0
        )
        
        assert result.value is False
        assert result.method_used == "llm"
        assert "Missing field" in result.structured_error
        assert "insufficient" in result.llm_reasoning
        assert result.execution_time_ms == 250.0 


def test_engine_fallback_strategy_strict_default():
    """Test that engine defaults to strict strategy."""
    engine = Engine()
    assert engine._fallback_strategy == "strict"
    assert engine._fallback_evaluator is None


def test_engine_fallback_strategy_auto_without_llm():
    """Test that auto strategy falls back to strict without LLM client."""
    engine = Engine(fallback_strategy="auto")
    # Should fall back to strict mode since no LLM client provided
    assert engine._fallback_strategy == "strict"
    assert engine._fallback_evaluator is None


def test_engine_fallback_strategy_auto_with_llm():
    """Test that auto strategy works with LLM client."""
    client = MockLLMClient()
    engine = Engine(fallback_strategy="auto", llm_client=client)
    assert engine._fallback_strategy == "auto"
    assert engine._fallback_evaluator is not None


def test_engine_fallback_strategy_invalid():
    """Test that invalid strategy raises error."""
    with pytest.raises(ValueError, match="Invalid fallback_strategy"):
        Engine(fallback_strategy="invalid")


def test_engine_reason_with_strict_strategy():
    """Test that strict strategy fails on evaluation errors."""
    rules = [Rule(
        id="test_rule",
        priority=100,
        condition="missing_field > 10",  # This will fail - field doesn't exist
        actions={"result": True}
    )]
    
    engine = Engine(rules=rules, fallback_strategy="strict")
    facts = Facts({"other_field": 5})
    
    result = engine.reason(facts)
    
    # Rule should not fire due to evaluation error
    assert len(result.fired_rules) == 0
    assert result.evaluation_method == "error"  # Error because all evaluations failed
    assert not result.fallback_triggered


def test_engine_reason_with_auto_strategy_success():
    """Test that auto strategy uses structured evaluation when it works."""
    rules = [Rule(
        id="test_rule",
        priority=100,
        condition="existing_field > 10",  # This will work
        actions={"result": True}
    )]
    
    client = MockLLMClient()
    engine = Engine(rules=rules, fallback_strategy="auto", llm_client=client)
    facts = Facts({"existing_field": 15})
    
    result = engine.reason(facts)
    
    # Rule should fire using structured evaluation
    assert len(result.fired_rules) == 1
    assert result.fired_rules[0] == "test_rule"
    assert result.evaluation_method == "structured"
    assert not result.fallback_triggered
    assert result.fallback_stats['structured_success_rate'] == 1.0


def test_engine_reason_with_auto_strategy_fallback():
    """Test that auto strategy falls back to LLM on evaluation errors."""
    rules = [Rule(
        id="test_rule",
        priority=100,
        condition="missing_field > 10",  # This will fail
        actions={"result": True}
    )]
    
    client = MockLLMClient()
    engine = Engine(rules=rules, fallback_strategy="auto", llm_client=client)
    facts = Facts({"other_field": 5})
    
    result = engine.reason(facts)
    
    # Rule should fire using LLM fallback
    assert len(result.fired_rules) == 1
    assert result.fired_rules[0] == "test_rule"
    assert result.evaluation_method == "llm_fallback"
    assert result.fallback_triggered
    assert result.fallback_stats['llm_fallback_rate'] > 0


def test_engine_reason_mixed_evaluation():
    """Test engine with multiple rules using different evaluation methods."""
    rules = [
        Rule(
            id="structured_rule",
            priority=100,
            condition="existing_field > 10",  # Will use structured
            actions={"structured_result": True}
        ),
        Rule(
            id="fallback_rule", 
            priority=90,
            condition="missing_field > 5",  # Will use LLM fallback
            actions={"fallback_result": True}
        )
    ]
    
    client = MockLLMClient()
    engine = Engine(rules=rules, fallback_strategy="auto", llm_client=client)
    facts = Facts({"existing_field": 15})
    
    result = engine.reason(facts)
    
    # Both rules should fire
    assert len(result.fired_rules) == 2
    assert "structured_rule" in result.fired_rules
    assert "fallback_rule" in result.fired_rules
    assert result.evaluation_method == "mixed"  # Mixed evaluation methods
    assert result.fallback_triggered
    assert result.fallback_stats['structured_success_rate'] < 1.0
    assert result.fallback_stats['llm_fallback_rate'] > 0


def test_fallback_evaluator_standalone():
    """Test FallbackEvaluator as standalone component."""
    # Mock structured evaluator that always fails
    mock_structured = Mock()
    mock_structured.evaluate.side_effect = EvaluationError("Missing field")
    mock_structured.extract_fields.return_value = ["missing_field"]
    
    # Mock prompt evaluator
    mock_prompt = Mock()
    mock_prompt.evaluate_prompt.return_value = True
    
    fallback_eval = FallbackEvaluator(mock_structured, mock_prompt)
    
    result = fallback_eval.prompt(
        "missing_field > 10",
        return_type="bool",
        context_facts={"other_field": 5}
    )
    
    assert result.method_used == "llm"
    assert result.value is True
    assert result.structured_error is not None


def test_fallback_stats_tracking():
    """Test that fallback statistics are tracked correctly."""
    rules = [
        Rule(id="rule1", priority=100, condition="field1 > 10", actions={"result1": True}),
        Rule(id="rule2", priority=90, condition="missing_field > 5", actions={"result2": True}),
        Rule(id="rule3", priority=80, condition="field3 > 1", actions={"result3": True})
    ]
    
    client = MockLLMClient()
    engine = Engine(rules=rules, fallback_strategy="auto", llm_client=client)
    facts = Facts({"field1": 15, "field3": 5})  # missing field2
    
    result = engine.reason(facts)
    
    stats = result.fallback_stats
    assert stats['total_evaluations'] == 3
    assert stats['structured_success_rate'] == 2/3  # rule1 and rule3 succeeded with structured
    assert stats['llm_fallback_rate'] == 1/3  # rule2 used LLM fallback
    assert stats['error_rate'] == 0.0  # no complete failures
    assert stats['fallback_triggered'] is True
    assert stats['evaluation_method'] == 'mixed'  # combination of structured and LLM


if __name__ == "__main__":
    pytest.main([__file__]) 