"""
Unit Tests for Core Engine Functionality
========================================

Tests for basic Engine operations, creation, reasoning, analysis, tracing, and explanations.
"""

import pytest
from symbolica import Engine, facts
from symbolica.core.models import Rule


class TestEngineCreation:
    """Test Engine creation and initialization."""
    
    @pytest.mark.unit
    @pytest.mark.critical
    def test_engine_basic_creation(self):
        """Test basic engine creation."""
        engine = Engine()
        
        assert engine._rules == []
        assert engine._evaluator is not None
        assert engine._executor is not None
        assert engine._dag_strategy is not None
    
    @pytest.mark.unit
    @pytest.mark.critical
    def test_engine_from_yaml_string(self, sample_yaml_rules):
        """Test engine creation from YAML string."""
        engine = Engine.from_yaml(sample_yaml_rules)
        
        analysis = engine.get_analysis()
        assert analysis['rule_count'] == 3
        assert 'high_value_customer' in analysis['rule_ids']
        assert 'risk_assessment' in analysis['rule_ids']
        assert 'account_bonus' in analysis['rule_ids']
    
    @pytest.mark.unit
    def test_engine_from_file(self, temp_directory, sample_yaml_rules):
        """Test engine creation from YAML file."""
        yaml_file = temp_directory / "test_rules.yaml"
        yaml_file.write_text(sample_yaml_rules)
        
        engine = Engine.from_file(yaml_file)
        
        analysis = engine.get_analysis()
        assert analysis['rule_count'] == 3
    
    @pytest.mark.unit
    def test_engine_from_directory(self, yaml_files_directory):
        """Test engine creation from directory with recursive search."""
        engine = Engine.from_directory(yaml_files_directory)
        
        analysis = engine.get_analysis()
        assert analysis['rule_count'] == 4  # 1 general + 2 customer + 1 security
        assert 'general_rule' in analysis['rule_ids']
        assert 'vip_customer' in analysis['rule_ids']
        assert 'loyalty_bonus' in analysis['rule_ids']
        assert 'high_risk_transaction' in analysis['rule_ids']


class TestEngineAnalysis:
    """Test engine analysis and metadata."""
    
    @pytest.mark.unit
    def test_get_analysis(self, sample_yaml_rules):
        """Test engine analysis functionality."""
        engine = Engine.from_yaml(sample_yaml_rules)
        
        analysis = engine.get_analysis()
        
        assert 'rule_count' in analysis
        assert 'rule_ids' in analysis
        assert 'avg_priority' in analysis
        
        assert analysis['rule_count'] == 3
        assert len(analysis['rule_ids']) == 3
        assert analysis['avg_priority'] > 0
    
    @pytest.mark.unit
    def test_analysis_empty_engine(self):
        """Test analysis of empty engine."""
        engine = Engine()
        
        analysis = engine.get_analysis()
        
        assert analysis['rule_count'] == 0
        assert analysis['rule_ids'] == []
        assert analysis['avg_priority'] == 0


class TestBasicEngine:
    """Basic engine functionality tests."""

    @pytest.mark.unit
    def test_engine_creation(self):
        """Test basic engine creation."""
        rules = [
            Rule(
                id="test_rule",
                priority=1,
                condition="amount > 100",
                actions={"status": "approved"}
            )
        ]
        engine = Engine(rules)
        assert engine.rule_count == 1
        assert engine.get_rule("test_rule").id == "test_rule"

    @pytest.mark.unit
    def test_simple_reasoning(self):
        """Test basic reasoning functionality."""
        rules = [
            Rule(
                id="basic_rule",
                priority=1,
                condition="value > 10",
                actions={"result": "high"}
            )
        ]
        engine = Engine(rules)
        
        result = engine.reason(facts(value=20))
        assert result.verdict["result"] == "high"
        assert "basic_rule" in result.fired_rules
        assert result.execution_time_ms > 0


class TestTracing:
    """Enhanced tracing functionality tests."""

    @pytest.mark.unit
    def test_detailed_tracing(self):
        """Test that tracing provides detailed information."""
        rules = [
            Rule(
                id="traced_rule",
                priority=1,
                condition="amount > 100 and status == 'active'",
                actions={"approved": True, "discount": 0.1}
            )
        ]
        engine = Engine(rules)
        
        test_facts = facts(amount=150, status='active')
        result = engine.reason(test_facts)
        
        # Check that tracing information is available
        assert "traced_rule" in result.fired_rules
        assert result.reasoning  # Should have reasoning information
        assert result.verdict["approved"] is True
        assert result.verdict["discount"] == 0.1

    @pytest.mark.unit
    def test_multiple_rules_tracing(self):
        """Test tracing with multiple rules firing."""
        rules = [
            Rule(id="rule1", priority=2, condition="amount > 50", actions={"tier": "bronze"}),
            Rule(id="rule2", priority=1, condition="amount > 100", actions={"tier": "silver", "bonus": True})
        ]
        engine = Engine(rules)
        
        result = engine.reason(facts(amount=150))
        
        # Both rules should fire, check tracing captures this
        assert "rule1" in result.fired_rules
        assert "rule2" in result.fired_rules
        assert result.verdict["tier"] == "silver"  # Higher priority rule overwrites
        assert result.verdict["bonus"] is True

    @pytest.mark.unit
    def test_non_firing_rule_tracing(self):
        """Test that non-firing rules don't appear in results."""
        rules = [
            Rule(id="fires", priority=1, condition="amount > 50", actions={"result": "fired"}),
            Rule(id="no_fire", priority=1, condition="amount > 200", actions={"result": "should_not_fire"})
        ]
        engine = Engine(rules)
        
        result = engine.reason(facts(amount=100))
        
        assert "fires" in result.fired_rules
        assert "no_fire" not in result.fired_rules
        assert result.verdict["result"] == "fired"


class TestExplanations:
    """Test explanation and reasoning output."""

    @pytest.mark.unit
    def test_basic_reasoning(self):
        """Test basic reasoning explanation."""
        rules = [
            Rule(
                id="explanation_rule",
                priority=1,
                condition="score > 80",
                actions={"grade": "A", "passed": True}
            )
        ]
        engine = Engine(rules)
        
        result = engine.reason(facts(score=95))
        
        assert result.reasoning  # Should have reasoning text
        assert "explanation_rule" in result.fired_rules
        assert result.verdict["grade"] == "A"
        assert result.verdict["passed"] is True

    @pytest.mark.unit
    def test_llm_context_generation(self):
        """Test LLM context generation for explanations."""
        rules = [
            Rule(
                id="context_rule",
                priority=1,
                condition="temperature > 30 and humidity < 60",
                actions={"climate": "dry_hot", "action": "increase_irrigation"}
            )
        ]
        engine = Engine(rules)
        
        result = engine.reason(facts(temperature=35, humidity=45))
        
        llm_context = result.get_llm_context()
        
        assert "temperature" in llm_context
        assert "humidity" in llm_context
        assert "climate" in llm_context
        assert "dry_hot" in llm_context

    @pytest.mark.unit
    def test_reasoning_json_output(self):
        """Test structured JSON reasoning output."""
        rules = [
            Rule(
                id="json_rule",
                priority=1,
                condition="value >= 100",
                actions={"category": "high_value", "eligible": True}
            )
        ]
        engine = Engine(rules)
        
        result = engine.reason(facts(value=150))
        
        reasoning_json = result.get_reasoning_json()
        
        assert "fired_rules" in reasoning_json
        assert "verdict" in reasoning_json
        assert "json_rule" in reasoning_json["fired_rules"]
        assert reasoning_json["verdict"]["category"] == "high_value"
        assert reasoning_json["verdict"]["eligible"] is True 