"""
Pytest Configuration and Shared Fixtures
========================================

Provides shared test fixtures and configuration for the entire test suite.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List

from symbolica import Engine, from_yaml
from symbolica.core import (
    Rule, RuleSet, Facts, Priority, Condition, Action, 
    rule_id, priority, condition, action_set, facts
)


@pytest.fixture
def sample_facts() -> Dict[str, Any]:
    """Basic test facts for most tests."""
    return {
        'amount': 1500,
        'status': 'active',
        'user_type': 'premium',
        'risk_score': 25,
        'country': 'US',
        'age': 28,
        'account_balance': 5000
    }


@pytest.fixture
def basic_rule() -> Rule:
    """Simple rule for unit testing."""
    return Rule(
        id=rule_id("test_rule"),
        priority=priority(100),
        condition=condition("amount > 1000"),
        actions=[action_set(tier='premium')]
    )


@pytest.fixture
def complex_rule_set() -> RuleSet:
    """Complex rule set for integration testing."""
    rules = [
        Rule(
            id=rule_id("high_value"),
            priority=priority(100),
            condition=condition("amount > 1000 and status == 'active'"),
            actions=[action_set(tier='premium', discount=0.15)]
        ),
        Rule(
            id=rule_id("risk_check"),
            priority=priority(90),
            condition=condition("risk_score > 50"),
            actions=[action_set(requires_review=True, tier='standard')]
        ),
        Rule(
            id=rule_id("country_check"),
            priority=priority(80),
            condition=condition("country not in ['US', 'CA', 'UK']"),
            actions=[action_set(international=True, fee=25)]
        ),
        Rule(
            id=rule_id("age_bonus"),
            priority=priority(70),
            condition=condition("age >= 25 and user_type == 'premium'"),
            actions=[action_set(age_bonus=50)]
        )
    ]
    return RuleSet(rules=rules)


@pytest.fixture
def sample_yaml_rules() -> str:
    """YAML rule definition for testing."""
    return """
rules:
  - id: high_value_customer
    priority: 100
    if: "amount > 1000 and status == 'active'"
    then:
      set:
        tier: premium
        discount: 0.15
        
  - id: risk_assessment
    priority: 90
    if:
      all:
        - "risk_score < 50"
        - "country in ['US', 'CA', 'UK']"
    then:
      set:
        approved: true
        risk_level: low
        
  - id: account_bonus
    priority: 80
    if: "account_balance > 5000 and user_type == 'premium'"
    then:
      set:
        bonus_eligible: true
        bonus_amount: 100
"""


@pytest.fixture
def nested_conditions_yaml() -> str:
    """Complex nested conditions for testing."""
    return """
rules:
  - id: complex_approval
    priority: 100
    if:
      any:
        - all:
          - "amount > 1000"
          - "status == 'active'"
        - all:
          - "user_type == 'premium'"
          - "account_balance > 10000"
    then:
      set:
        approved: true
        approval_reason: "high_value_or_premium"
        
  - id: fraud_detection
    priority: 200
    if:
      any:
        - "risk_score > 80"
        - all:
          - "amount > 5000"
          - "country not in ['US', 'CA']"
          - "age < 21"
    then:
      set:
        flagged: true
        review_required: true
"""


@pytest.fixture
def temp_directory():
    """Temporary directory for file operations."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def yaml_files_directory(temp_directory, sample_yaml_rules):
    """Directory with sample YAML files."""
    yaml_dir = temp_directory / "rules"
    yaml_dir.mkdir()
    
    # Create multiple YAML files
    (yaml_dir / "main_rules.yaml").write_text(sample_yaml_rules)
    
    additional_rules = """
rules:
  - id: late_payment_fee
    priority: 60
    if: "days_overdue > 30"
    then:
      set:
        late_fee: 25
        collection_eligible: true
"""
    (yaml_dir / "payment_rules.yaml").write_text(additional_rules)
    
    return yaml_dir


@pytest.fixture
def engine_with_rules(sample_yaml_rules) -> Engine:
    """Engine instance with pre-loaded rules."""
    return from_yaml(sample_yaml_rules)


@pytest.fixture
def performance_facts() -> List[Dict[str, Any]]:
    """Large dataset for performance testing."""
    facts_list = []
    for i in range(1000):
        facts_list.append({
            'amount': 500 + (i * 10),
            'status': 'active' if i % 3 == 0 else 'pending',
            'user_type': 'premium' if i % 4 == 0 else 'standard',
            'risk_score': i % 100,
            'country': ['US', 'CA', 'UK', 'DE', 'FR'][i % 5],
            'age': 18 + (i % 50),
            'account_balance': 1000 + (i * 100),
            'user_id': f"user_{i:04d}"
        })
    return facts_list


# Test data constants
INVALID_YAML_SAMPLES = [
    # Missing required fields
    """
rules:
  - if: "amount > 1000"
    then:
      set:
        tier: premium
""",
    # Invalid YAML syntax
    """
rules:
  - id: test
    if: amount > 1000
    then:
      set:
        tier: premium
        invalid: [unclosed list
""",
    # Invalid expression syntax
    """
rules:
  - id: invalid_expr
    if: "amount >"
    then:
      set:
        tier: premium
""",
]


ERROR_CASES = [
    {
        'name': 'division_by_zero',
        'facts': {'amount': 1000, 'divisor': 0},
        'condition': 'amount / divisor > 100'
    },
    {
        'name': 'undefined_field',
        'facts': {'amount': 1000},
        'condition': 'nonexistent_field > 500'
    },
    {
        'name': 'type_error',
        'facts': {'amount': '1000'},
        'condition': 'amount + 500 > 2000'
    },
] 