#!/usr/bin/env python3
"""
Schema Validation Test Example
==============================

Demonstrates how Symbolica's schema validation system enforces YAML structure
and prevents use of reserved keywords.
"""

from symbolica import Engine, facts
from symbolica.core.infrastructure.loader import RuleLoader
from symbolica.core.infrastructure.exceptions import ValidationError


def test_valid_schema():
    """Test a correctly structured YAML file."""
    print("Testing valid schema...")
    
    valid_yaml = """
    rules:
      - id: "customer_approval"
        priority: 100
        condition: "credit_score > 650"
        facts:
          risk_level: credit_score / 100
          approval_tier: "standard"
        actions:
          approved: true
          credit_limit: annual_income * 2
        tags: ["approval", "credit"]
    """
    
    try:
        engine = Engine.from_yaml(valid_yaml)
        print("✓ Valid schema accepted")
        
        # Test execution
        result = engine.reason(facts(credit_score=720, annual_income=50000))
        print(f"✓ Execution successful: approved={result.verdict['approved']}")
        print(f"  Intermediate facts: {result.intermediate_facts}")
        
    except ValidationError as e:
        print(f"✗ Unexpected validation error: {e}")


def test_reserved_keyword_rule_id():
    """Test using reserved keyword as rule ID."""
    print("\nTesting reserved keyword as rule ID...")
    
    invalid_yaml = """
    rules:
      - id: "condition"  # Reserved keyword!
        condition: "True"
        actions:
          result: "test"
    """
    
    try:
        engine = Engine.from_yaml(invalid_yaml)
        print("✗ Should have rejected reserved keyword as rule ID")
    except ValidationError as e:
        print(f"✓ Correctly rejected reserved keyword: {e}")


def test_reserved_keyword_fact_name():
    """Test using reserved keyword as fact name."""
    print("\nTesting reserved keyword as fact name...")
    
    invalid_yaml = """
    rules:
      - id: "test_rule"
        condition: "True"
        facts:
          sum: 10  # Reserved keyword!
        actions:
          result: "test"
    """
    
    try:
        engine = Engine.from_yaml(invalid_yaml)
        print("✗ Should have rejected reserved keyword as fact name")
    except ValidationError as e:
        print(f"✓ Correctly rejected reserved keyword: {e}")


def test_reserved_keyword_action_name():
    """Test using reserved keyword as action name."""
    print("\nTesting reserved keyword as action name...")
    
    invalid_yaml = """
    rules:
      - id: "test_rule"
        condition: "True"
        actions:
          len: 5  # Reserved keyword!
    """
    
    try:
        engine = Engine.from_yaml(invalid_yaml)
        print("✗ Should have rejected reserved keyword as action name")
    except ValidationError as e:
        print(f"✓ Correctly rejected reserved keyword: {e}")


def test_unknown_top_level_key():
    """Test unknown top-level key."""
    print("\nTesting unknown top-level key...")
    
    invalid_yaml = """
    rules:
      - id: "test_rule"
        condition: "True"
        actions:
          result: "test"
    unknown_field: "invalid"  # Unknown top-level key!
    """
    
    try:
        engine = Engine.from_yaml(invalid_yaml)
        print("✗ Should have rejected unknown top-level key")
    except ValidationError as e:
        print(f"✓ Correctly rejected unknown top-level key: {e}")


def test_unknown_rule_field():
    """Test unknown rule field."""
    print("\nTesting unknown rule field...")
    
    invalid_yaml = """
    rules:
      - id: "test_rule"
        condition: "True"
        actions:
          result: "test"
        unknown_field: "invalid"  # Unknown rule field!
    """
    
    try:
        engine = Engine.from_yaml(invalid_yaml)
        print("✗ Should have rejected unknown rule field")
    except ValidationError as e:
        print(f"✓ Correctly rejected unknown rule field: {e}")


def test_invalid_field_types():
    """Test invalid field types."""
    print("\nTesting invalid field types...")
    
    invalid_yaml = """
    rules:
      - id: "test_rule"
        priority: "high"  # Should be integer!
        condition: "True"
        actions:
          result: "test"
    """
    
    try:
        engine = Engine.from_yaml(invalid_yaml)
        print("✗ Should have rejected invalid field type")
    except ValidationError as e:
        print(f"✓ Correctly rejected invalid field type: {e}")


def test_missing_required_fields():
    """Test missing required fields."""
    print("\nTesting missing required fields...")
    
    invalid_yaml = """
    rules:
      - id: "test_rule"
        # Missing condition!
        actions:
          result: "test"
    """
    
    try:
        engine = Engine.from_yaml(invalid_yaml)
        print("✗ Should have rejected missing required fields")
    except ValidationError as e:
        print(f"✓ Correctly rejected missing required fields: {e}")


def test_invalid_structured_condition():
    """Test invalid structured condition keyword."""
    print("\nTesting invalid structured condition keyword...")
    
    invalid_yaml = """
    rules:
      - id: "test_rule"
        condition:
          invalid_keyword: ["x > 5"]  # Invalid condition keyword!
        actions:
          result: "test"
    """
    
    try:
        engine = Engine.from_yaml(invalid_yaml)
        print("✗ Should have rejected invalid condition keyword")
    except ValidationError as e:
        print(f"✓ Correctly rejected invalid condition keyword: {e}")


def show_schema_documentation():
    """Show the schema documentation."""
    print("\n" + "="*60)
    print("SYMBOLICA YAML SCHEMA DOCUMENTATION")
    print("="*60)
    
    loader = RuleLoader()
    print(loader.get_schema_documentation())


def show_reserved_keywords():
    """Show all reserved keywords."""
    print("\n" + "="*60)
    print("RESERVED KEYWORDS SAMPLE")
    print("="*60)
    
    loader = RuleLoader()
    keywords = sorted(loader.get_reserved_keywords())
    
    print(f"Total reserved keywords: {len(keywords)}")
    print("\nSample keywords (first 30):")
    for i, keyword in enumerate(keywords[:30]):
        if i % 6 == 0:
            print()
        print(f"  {keyword:<12}", end="")
    print("\n...")


def main():
    """Run all schema validation tests."""
    print("Symbolica Schema Validation Test")
    print("=" * 40)
    
    # Test valid cases
    test_valid_schema()
    
    # Test invalid cases
    test_reserved_keyword_rule_id()
    test_reserved_keyword_fact_name() 
    test_reserved_keyword_action_name()
    test_unknown_top_level_key()
    test_unknown_rule_field()
    test_invalid_field_types()
    test_missing_required_fields()
    test_invalid_structured_condition()
    
    # Show documentation
    show_schema_documentation()
    show_reserved_keywords()
    
    print("\n" + "="*60)
    print("SCHEMA VALIDATION SUMMARY")
    print("="*60)
    print("✓ Schema validation enforces standardized YAML structure")
    print("✓ Reserved keywords are protected from user misuse")
    print("✓ Field types are validated for consistency")
    print("✓ Unknown fields are rejected to prevent typos")
    print("✓ Required fields are enforced")
    print("✓ Structured conditions use valid keywords only")
    print()
    print("This ensures:")
    print("- Consistent AST structure across all rule files")
    print("- No conflicts with system functionality")
    print("- Better error messages for common mistakes")
    print("- Predictable behavior for developers")


if __name__ == "__main__":
    main() 