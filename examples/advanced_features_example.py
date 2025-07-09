"""
Advanced Features Example
========================

Comprehensive demonstration of Symbolica's advanced features:
- Rule serialization with hot-reload
- Enhanced error handling and validation
- Deep tracing and debugging
- Performance analysis and optimization
"""

import json
import time
from pathlib import Path
from typing import Dict, Any

# Import Symbolica components
from symbolica import Engine, from_yaml, Facts
from symbolica._internal.serialization import (
    RulePackSerializer, HotReloadManager, SerializationFormat,
    save_rules, load_rules
)
from symbolica._internal.validation import (
    EnhancedValidator, ValidationLevel, ValidationResult,
    validate_facts, validate_expression, validate_rule_dict
)
from symbolica._internal.tracing import (
    ExecutionTracer, TraceLevel, TraceAnalyzer,
    create_tracer, analyze_traces
)


def demonstrate_serialization():
    """Demonstrate rule serialization and hot-reload capabilities."""
    print("=== Rule Serialization Demo ===")
    
    # Create sample rules
    rules_yaml = """
    rules:
      - id: customer_validation
        priority: 100
        if: customer_type == "premium" and account_balance > 1000
        then:
          set:
            tier: gold
            discount: 0.15
        tags: [customer, validation]
        
      - id: risk_assessment
        priority: 90
        if: transaction_amount > 10000 and risk_score > 0.8
        then:
          set:
            requires_approval: true
            alert_level: high
        tags: [risk, security]
        
      - id: loyalty_bonus
        priority: 50
        if: customer_loyalty_years >= 5 and tier == "gold"
        then:
          set:
            bonus_eligible: true
            bonus_rate: 0.05
        tags: [loyalty, rewards]
    """
    
    # Create engine and rule set
    engine = from_yaml(rules_yaml)
    rule_set = engine.rule_set
    
    # Demonstrate different serialization formats
    serializer = RulePackSerializer()
    
    print("\n1. Serializing to different formats:")
    
    # JSON format
    json_result = serializer.serialize(
        rule_set, 
        Path("temp_rules.json"), 
        SerializationFormat.JSON
    )
    print(f"JSON serialization: {json_result['size_bytes']} bytes in {json_result['serialization_time_ms']:.2f}ms")
    
    # Compressed JSON
    compressed_result = serializer.serialize(
        rule_set, 
        Path("temp_rules.json.gz"), 
        SerializationFormat.COMPRESSED_JSON
    )
    print(f"Compressed JSON: {compressed_result['size_bytes']} bytes in {compressed_result['serialization_time_ms']:.2f}ms")
    print(f"Compression ratio: {compressed_result['size_bytes'] / json_result['size_bytes']:.2f}")
    
    # Binary format  
    binary_result = serializer.serialize(
        rule_set, 
        Path("temp_rules.pkl"), 
        SerializationFormat.BINARY
    )
    print(f"Binary serialization: {binary_result['size_bytes']} bytes in {binary_result['serialization_time_ms']:.2f}ms")
    
    print("\n2. Loading and validating:")
    
    # Load from JSON
    load_result = serializer.deserialize(Path("temp_rules.json"))
    print(f"JSON load: {load_result.load_time_ms:.2f}ms, success: {load_result.success}")
    print(f"Loaded {load_result.rule_set.rule_count} rules")
    
    # Load from cache (should be faster)
    cached_result = serializer.deserialize(Path("temp_rules.json"))
    print(f"Cached load: {cached_result.load_time_ms:.2f}ms, from cache: {cached_result.from_cache}")
    
    # Demonstrate metadata
    if load_result.metadata:
        print(f"Metadata: version={load_result.metadata.version}, rules={load_result.metadata.rule_count}")
    
    print("\n3. Hot-reload demonstration:")
    
    # Create hot-reload manager
    hot_reload = HotReloadManager(serializer)
    
    # Callback for file changes
    def on_file_change(path, rule_set, metadata):
        print(f"File {path} changed! Reloaded {rule_set.rule_count} rules")
    
    # Watch file for changes
    hot_reload.watch_file(Path("temp_rules.json"), on_file_change)
    
    # Simulate file change (in real use, you'd modify the file externally)
    time.sleep(0.1)
    
    # Modify and re-save to trigger hot-reload
    modified_rules = rule_set.rules + [rule_set.rules[0]]  # Duplicate first rule
    from symbolica.core import RuleSet
    modified_rule_set = RuleSet(modified_rules)
    
    serializer.serialize(modified_rule_set, Path("temp_rules.json"), SerializationFormat.JSON)
    time.sleep(0.1)  # Give hot-reload time to detect change
    
    # Clean up
    hot_reload.stop_monitoring()
    
    print(f"Hot-reload status: {hot_reload.get_watch_status()}")
    
    # Clean up temp files
    for temp_file in [Path("temp_rules.json"), Path("temp_rules.json.gz"), Path("temp_rules.pkl")]:
        if temp_file.exists():
            temp_file.unlink()


def demonstrate_error_handling():
    """Demonstrate enhanced error handling and validation."""
    print("\n=== Enhanced Error Handling Demo ===")
    
    validator = EnhancedValidator(strict=False)
    
    print("\n1. Facts validation:")
    
    # Test various facts scenarios
    test_cases = [
        {},  # Empty facts
        {"customer_type": "premium", "balance": 1000},  # Good facts
        {"customer-type": "premium", "balance": float('inf')},  # Problematic facts
        {"and": "reserved", "balance": "not_a_number"},  # Reserved word and type issues
        {123: "invalid_key"},  # Invalid key type
    ]
    
    for i, facts_data in enumerate(test_cases):
        print(f"\nTest case {i+1}: {facts_data}")
        result = validator.validate_facts(facts_data)
        
        if result.errors:
            print("  Errors:")
            for error in result.errors:
                print(f"    - {error}")
        
        if result.warnings:
            print("  Warnings:")
            for warning in result.warnings:
                print(f"    - {warning}")
    
    print("\n2. Expression validation:")
    
    # Test various expressions
    expressions = [
        "customer_type == 'premium'",  # Good
        "customer_type = 'premium'",   # Assignment instead of comparison
        "customer_type == premium",    # Unquoted string
        "customer_type.equals('premium')",  # Java-style method
        "customer_type == 'premium' AND balance > 1000",  # SQL-style operator
        "((customer_type == 'premium')",  # Unbalanced parentheses
        "unknown_field > 100",  # Unknown field
        "",  # Empty expression
    ]
    
    available_fields = {"customer_type", "balance", "account_age"}
    
    for expr in expressions:
        print(f"\nExpression: '{expr}'")
        result = validator.validate_expression(expr, "test", available_fields)
        
        if result.errors:
            for error in result.errors:
                print(f"  ERROR: {error}")
        
        if result.warnings:
            for warning in result.warnings:
                print(f"  WARNING: {warning}")
    
    print("\n3. Rule validation:")
    
    # Test rule validation
    test_rules = [
        {
            "id": "good_rule",
            "if": "customer_type == 'premium'",
            "then": {"set": {"tier": "gold"}},
            "priority": 100
        },
        {
            "id": "bad_rule",
            "if": "customer_type = 'premium'",  # Assignment error
            "then": {"set": {}},  # Empty set
            "priority": -10,  # Negative priority
            "tags": ["valid", "", "tags"]  # Empty tag
        },
        {
            "if": "customer_type == 'premium'",  # Missing ID
            "then": "invalid_action_format"  # Wrong action format
        }
    ]
    
    for i, rule_data in enumerate(test_rules):
        print(f"\nRule {i+1}: {rule_data.get('id', 'unnamed')}")
        result = validator.validate_rule(rule_data, f"rule_{i+1}", i+1)
        
        for issue in result.issues:
            print(f"  {issue.level.value.upper()}: {issue.message}")
            if issue.suggestion:
                print(f"    Suggestion: {issue.suggestion}")
    
    print("\n4. Rule set validation:")
    
    # Test duplicate rule IDs
    duplicate_rules = [
        {"id": "duplicate", "if": "True", "then": {"set": {"a": 1}}},
        {"id": "duplicate", "if": "True", "then": {"set": {"b": 2}}},
        {"id": "unique", "if": "True", "then": {"set": {"c": 3}}}
    ]
    
    result = validator.validate_rule_set(duplicate_rules)
    print(f"Rule set validation: {len(result.errors)} errors, {len(result.warnings)} warnings")
    
    for issue in result.issues:
        print(f"  {issue.level.value.upper()}: {issue.message}")


def demonstrate_tracing():
    """Demonstrate deep tracing and debugging capabilities."""
    print("\n=== Deep Tracing Demo ===")
    
    # Create rules for tracing
    rules_yaml = """
    rules:
      - id: high_value_check
        priority: 100
        if: transaction_amount > 5000
        then:
          set:
            high_value: true
            review_required: true
        tags: [transaction, validation]
        
      - id: customer_tier_check
        priority: 90
        if: customer_type == "premium" and account_balance > 10000
        then:
          set:
            tier: platinum
            special_offers: true
        tags: [customer, tier]
        
      - id: risk_evaluation
        priority: 80
        if: risk_score > 0.7 and transaction_amount > 1000
        then:
          set:
            risk_level: high
            manual_review: true
        tags: [risk, security]
        
      - id: loyalty_check
        priority: 70
        if: customer_loyalty_years >= 3 and tier == "platinum"
        then:
          set:
            loyalty_bonus: 100
            vip_status: true
        tags: [loyalty, rewards]
        
      - id: never_fires
        priority: 60
        if: impossible_condition == "never_true"
        then:
          set:
            this_never_happens: true
        tags: [test]
    """
    
    engine = from_yaml(rules_yaml)
    
    print("\n1. Basic tracing:")
    
    # Create tracer with basic level
    tracer = create_tracer(TraceLevel.BASIC)
    
    # Test facts
    facts = Facts({
        "transaction_amount": 7500,
        "customer_type": "premium",
        "account_balance": 15000,
        "risk_score": 0.8,
        "customer_loyalty_years": 4
    })
    
    # Execute with tracing
    result = engine.reason(facts, tracer=tracer)
    print(f"Execution result: {result.verdict}")
    print(f"Rules fired: {len(result.fired_rules)}")
    print(f"Field changes: {len(result.field_changes)}")
    
    # Get and analyze trace
    traces = tracer.get_trace_history()
    if traces:
        latest_trace = traces[-1]
        print(f"\nTrace analysis:")
        print(f"  Total time: {latest_trace.total_execution_time_ms:.2f}ms")
        print(f"  Success rate: {latest_trace.success_rate:.1f}%")
        print(f"  Rules evaluated: {latest_trace.total_rules_evaluated}")
        print(f"  Rules fired: {latest_trace.total_rules_fired}")
        
        # Explain execution
        print(f"\nExecution explanation:")
        print(f"  {latest_trace.explain_execution()}")
        
        # Explain specific rules
        for rule_trace in latest_trace.rule_traces:
            print(f"  - {rule_trace.explain_outcome()}")
    
    print("\n2. Detailed tracing with performance analysis:")
    
    # Create detailed tracer
    detailed_tracer = create_tracer(TraceLevel.DETAILED)
    
    # Run multiple executions with different facts
    test_scenarios = [
        {"transaction_amount": 3000, "customer_type": "basic", "account_balance": 5000, "risk_score": 0.3},
        {"transaction_amount": 8000, "customer_type": "premium", "account_balance": 20000, "risk_score": 0.5},
        {"transaction_amount": 15000, "customer_type": "premium", "account_balance": 50000, "risk_score": 0.9},
        {"transaction_amount": 2000, "customer_type": "gold", "account_balance": 8000, "risk_score": 0.2},
        {"transaction_amount": 12000, "customer_type": "premium", "account_balance": 30000, "risk_score": 0.6},
    ]
    
    for i, scenario in enumerate(test_scenarios):
        facts = Facts(scenario)
        result = engine.reason(facts, tracer=detailed_tracer)
        print(f"Scenario {i+1}: {len(result.fired_rules)} rules fired in {result.execution_time_ms:.2f}ms")
    
    print("\n3. Performance analysis:")
    
    # Analyze performance across all traces
    performance = detailed_tracer.analyze_performance()
    print(f"Overall performance:")
    print(f"  Average execution time: {performance.get('avg_execution_time_ms', 0):.2f}ms")
    print(f"  Average success rate: {performance.get('avg_success_rate', 0):.1f}%")
    print(f"  Total executions: {performance.get('total_executions', 0)}")
    
    # Rule coverage
    coverage = detailed_tracer.get_rule_coverage()
    print(f"\nRule coverage:")
    for rule_id, count in coverage.items():
        rule_perf = detailed_tracer.analyze_performance(rule_id)
        fire_rate = rule_perf.get('fire_rate', 0) * 100
        avg_time = rule_perf.get('avg_time_ms', 0)
        print(f"  {rule_id}: {count} executions, {fire_rate:.1f}% fire rate, {avg_time:.2f}ms avg")
    
    # Field access statistics
    field_stats = detailed_tracer.get_field_access_stats()
    print(f"\nField access statistics:")
    for field, count in sorted(field_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {field}: {count} accesses")
    
    print("\n4. Trace analysis and debugging:")
    
    # Create trace analyzer
    all_traces = detailed_tracer.get_trace_history()
    analyzer = TraceAnalyzer(all_traces)
    
    # Find bottlenecks
    bottlenecks = analyzer.find_bottlenecks(threshold_ms=1.0)
    if bottlenecks:
        print(f"\nPerformance bottlenecks:")
        for bottleneck in bottlenecks:
            print(f"  - {bottleneck['recommendation']}")
    
    # Field usage analysis
    field_usage = analyzer.analyze_field_usage()
    print(f"\nField usage analysis:")
    print(f"  Most read fields: {field_usage['most_read_fields'][:3]}")
    print(f"  Most written fields: {field_usage['most_written_fields'][:3]}")
    
    # Debugging recommendations
    recommendations = analyzer.get_debugging_recommendations()
    if recommendations:
        print(f"\nDebugging recommendations:")
        for rec in recommendations:
            print(f"  - {rec}")
    
    print("\n5. Why did/didn't rules fire?")
    
    # Explain specific rule outcomes
    if all_traces:
        latest_trace = all_traces[-1]
        
        print(f"\nRule firing explanations:")
        for rule_id in ["high_value_check", "never_fires", "loyalty_check"]:
            explanation = latest_trace.explain_execution(rule_id)
            print(f"  {rule_id}: {explanation}")
    
    print("\n6. Export traces for analysis:")
    
    # Export traces to JSON
    export_path = Path("trace_export.json")
    detailed_tracer.export_traces(export_path)
    
    # Load and show summary
    with open(export_path) as f:
        exported_data = json.load(f)
    
    print(f"Exported {len(exported_data['traces'])} traces")
    print(f"Summary: {exported_data['summary']}")
    
    # Clean up
    export_path.unlink()


def demonstrate_integration():
    """Demonstrate integration of all advanced features."""
    print("\n=== Integration Demo ===")
    
    # Create a comprehensive example that uses all features
    rules_yaml = """
    rules:
      - id: comprehensive_rule
        priority: 100
        if: customer_type == "premium" and transaction_amount > 5000 and risk_score < 0.5
        then:
          set:
            approved: true
            tier: gold
            bonus: 0.1
        tags: [premium, approval]
        
      - id: error_prone_rule
        priority: 90
        if: faulty_field == "test" and another_field > 100
        then:
          set:
            error_test: true
        tags: [test, error]
    """
    
    print("1. Creating engine with validation:")
    
    # Validate rules before creating engine
    import yaml
    rules_data = yaml.safe_load(rules_yaml)
    validator = EnhancedValidator()
    validation_result = validator.validate_rule_set(rules_data['rules'])
    
    if validation_result.errors:
        print("Rule validation errors:")
        for error in validation_result.errors:
            print(f"  - {error}")
    
    if validation_result.warnings:
        print("Rule validation warnings:")
        for warning in validation_result.warnings:
            print(f"  - {warning}")
    
    # Create engine
    engine = from_yaml(rules_yaml)
    
    print("\n2. Serialize and load rules:")
    
    # Serialize rules
    serializer = RulePackSerializer()
    rule_pack_path = Path("comprehensive_rules.json")
    
    serialize_result = serializer.serialize(
        engine.rule_set, 
        rule_pack_path, 
        SerializationFormat.JSON
    )
    print(f"Serialized in {serialize_result['serialization_time_ms']:.2f}ms")
    
    # Load rules
    load_result = serializer.deserialize(rule_pack_path)
    print(f"Loaded in {load_result.load_time_ms:.2f}ms")
    
    print("\n3. Execute with comprehensive tracing:")
    
    # Create tracer
    tracer = create_tracer(TraceLevel.DETAILED)
    
    # Test facts (some will cause validation warnings)
    facts = Facts({
        "customer_type": "premium",
        "transaction_amount": 7500,
        "risk_score": 0.3,
        # Note: missing 'faulty_field' and 'another_field' for second rule
    })
    
    # Validate facts
    expected_fields = {"customer_type", "transaction_amount", "risk_score", "faulty_field", "another_field"}
    facts_validation = validate_facts(facts.data, expected_fields)
    
    if facts_validation.warnings:
        print("Facts validation warnings:")
        for warning in facts_validation.warnings:
            print(f"  - {warning}")
    
    # Execute with tracing
    result = engine.reason(facts, tracer=tracer)
    
    print(f"\nExecution completed:")
    print(f"  Verdict: {result.verdict}")
    print(f"  Time: {result.execution_time_ms:.2f}ms")
    print(f"  Rules fired: {len(result.fired_rules)}")
    
    # Get trace and analyze
    traces = tracer.get_trace_history()
    if traces:
        trace = traces[-1]
        
        print(f"\nTrace analysis:")
        print(f"  {trace.explain_execution()}")
        
        # Show individual rule explanations
        for rule_trace in trace.rule_traces:
            print(f"  - {rule_trace.explain_outcome()}")
    
    print("\n4. Performance and debugging insights:")
    
    # Performance analysis
    performance = tracer.analyze_performance()
    print(f"Performance summary:")
    print(f"  Avg execution time: {performance.get('avg_execution_time_ms', 0):.2f}ms")
    print(f"  Field accesses: {performance.get('field_access_stats', {})}")
    
    # Trace analysis
    if traces:
        analyzer = TraceAnalyzer(traces)
        recommendations = analyzer.get_debugging_recommendations()
        
        if recommendations:
            print(f"\nDebugging recommendations:")
            for rec in recommendations:
                print(f"  - {rec}")
    
    # Clean up
    rule_pack_path.unlink()


def main():
    """Run all demonstrations."""
    print("Symbolica Advanced Features Demonstration")
    print("=" * 50)
    
    try:
        demonstrate_serialization()
        demonstrate_error_handling()
        demonstrate_tracing()
        demonstrate_integration()
        
        print("\n" + "=" * 50)
        print("All demonstrations completed successfully!")
        
    except Exception as e:
        print(f"\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 