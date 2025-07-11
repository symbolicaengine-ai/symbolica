"""
Pytest Configuration and Shared Fixtures
========================================

Provides shared test fixtures for the simplified Symbolica engine.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List

from symbolica import Engine
from symbolica.core import Rule, Facts, ExecutionResult, facts


# Pytest markers configuration
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Fast, isolated unit tests")
    config.addinivalue_line("markers", "integration: End-to-end integration tests")
    config.addinivalue_line("markers", "slow: Tests that take significant time (>1s)")
    config.addinivalue_line("markers", "critical: Essential tests that must pass")
    config.addinivalue_line("markers", "extended: Extended test coverage for edge cases")
    config.addinivalue_line("markers", "performance: Performance and benchmark tests")


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
        'account_balance': 5000,
        'tags': ['vip', 'loyalty'],
        'payment_history': [100, 95, 88, 92, 98],
        'last_login': None,
        'account_verified': True
    }


@pytest.fixture
def simple_rule_dict() -> Dict[str, Any]:
    """Simple rule data for unit testing."""
    return {
        'id': 'test_rule',
        'priority': 100,
        'condition': 'amount > 1000',
        'actions': {'tier': 'premium', 'approved': True},
        'tags': ['test', 'simple']
    }


@pytest.fixture
def sample_yaml_rules() -> str:
    """YAML rule definition for testing."""
    return """
rules:
  - id: high_value_customer
    priority: 100
    if: "amount > 1000 and status == 'active'"
    then:
        tier: premium
        discount: 0.15
    tags: [customer, premium]

  - id: risk_assessment
    priority: 90
    if:
      all:
        - "risk_score < 50"
        - "country in ['US', 'CA', 'UK']"
    then:
        approved: true
        risk_level: low
    tags: [risk, approval]

  - id: account_bonus
    priority: 80
    if: "account_balance > 5000 and user_type == 'premium'"
    then:
        bonus_eligible: true
        bonus_amount: 100
    tags: [bonus, reward]
"""


@pytest.fixture
def structured_conditions_yaml() -> str:
    """Complex structured conditions for testing."""
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
        approved: true
        approval_reason: "high_value_or_premium"
    tags: [approval, complex]

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
        flagged: true
        review_required: true
    tags: [fraud, security]

  - id: nested_logic
    priority: 150
    if:
      all:
        - not: "status == 'inactive'"
        - any:
          - "user_type == 'vip'"
          - all:
            - "account_balance > 50000"
            - "age >= 25"
    then:
      special_treatment: true
      priority_support: true
    tags: [vip, nested]
"""


@pytest.fixture
def temp_directory():
    """Temporary directory for file operations."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def yaml_files_directory(temp_directory):
    """Directory with sample YAML files for testing directory loading."""
    yaml_dir = temp_directory / "rules"
    yaml_dir.mkdir()

    # Create subdirectories
    (yaml_dir / "customer").mkdir()
    (yaml_dir / "security").mkdir()

    # Main rules file
    main_rules = """
rules:
  - id: general_rule
    priority: 50
    if: "status == 'active'"
    then:
      processed: true
    tags: [general]
"""
    (yaml_dir / "main_rules.yaml").write_text(main_rules)

    # Customer rules
    customer_rules = """
rules:
  - id: vip_customer
    priority: 100
    if: "user_type == 'vip'"
    then:
      special_treatment: true
      priority_support: true
    tags: [customer, vip]

  - id: loyalty_bonus
    priority: 80
    if: "loyalty_years >= 5"
    then:
      loyalty_bonus: 500
      bonus_rate: 0.05
    tags: [customer, loyalty]
"""
    (yaml_dir / "customer" / "customer_rules.yaml").write_text(customer_rules)

    # Security rules
    security_rules = """
rules:
  - id: high_risk_transaction
    priority: 200
    if: "amount > 10000 and risk_score > 70"
    then:
      requires_approval: true
      alert_level: high
    tags: [security, risk]
"""
    (yaml_dir / "security" / "security_rules.yaml").write_text(security_rules)

    return yaml_dir


@pytest.fixture
def performance_facts() -> List[Dict[str, Any]]:
    """Dataset for performance testing."""
    facts_list = []
    for i in range(50):  # Reduced from 500 to 50 for faster tests
        facts_list.append({
            'amount': 500 + (i * 10),
            'status': 'active' if i % 3 == 0 else 'pending',
            'user_type': 'premium' if i % 4 == 0 else 'standard',
            'risk_score': i % 100,
            'country': ['US', 'CA', 'UK'][i % 3],  # Reduced countries
            'age': 18 + (i % 50),
            'user_id': f"user_{i:02d}"  # Shorter ID format
        })
    return facts_list


# Essential test data constants
INVALID_YAML_SAMPLES = [
    # Missing required fields
    """
rules:
  - if: "amount > 1000"
    then:
        tier: premium
""",
    # Invalid YAML syntax
    """
rules:
  - id: test
    if: amount > 1000
    then:
        tier: premium
        invalid: [unclosed list
""",
]


ERROR_TEST_CASES = [
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
]


EXPRESSION_TEST_CASES = [
    # Basic comparisons
    {'expr': 'amount > 1000', 'expected': True},
    {'expr': 'amount == 1500', 'expected': True},
    {'expr': 'status == "active"', 'expected': True},

    # Boolean logic
    {'expr': 'amount > 1000 and status == "active"', 'expected': True},
    {'expr': 'not status == "inactive"', 'expected': True},

    # List operations
    {'expr': '"vip" in tags', 'expected': True},
    {'expr': 'len(payment_history) >= 5', 'expected': True},

    # Null checks and arithmetic
    {'expr': 'last_login == None', 'expected': True},
] 