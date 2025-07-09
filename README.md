# Symbolica: Deterministic Rule Engine for AI Agents

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Performance](https://img.shields.io/badge/performance-sub--millisecond-brightgreen.svg)](https://github.com/anibjoshi/symbolica)


**Symbolica** is a rule engine for AI agents that need deterministic, explainable reasoning. Replace unreliable LLM reasoning with fast, consistent rule evaluation.

## Why Symbolica?

AI agents need **deterministic logic** for critical decisions. Instead of hoping an LLM will reason correctly, define your logic once and get consistent results every time.

**Perfect for:**
- **AI Agent Decision Making** - Replace LLM reasoning with reliable rules
- **Business Logic** - Customer approval, pricing, risk assessment  
- **Workflow Automation** - Multi-step processes with rule chaining
- **Compliance** - Policy enforcement with audit trails

## Key Features

- **Sub-millisecond execution** - 6,000+ executions per second
- **Custom functions** - Extend rules with safe lambda functions for complex business logic
- **Temporal functions** - Time-series analysis and pattern detection for monitoring & alerting
- **Clean explanations** - Perfect for LLM integration
- **Rule chaining** - Create workflows by triggering rules
- **Backward chaining** - Find which rules can achieve goals
- **Flexible syntax** - Simple strings or nested logical structures
- **Zero dependencies** - Just PyYAML

## Installation

```bash
pip install symbolica
```

## Quick Start

### Define Rules
```yaml
rules:
  - id: "vip_customer"
    priority: 100
    condition: "customer_tier == 'vip' and credit_score > 750"
    actions:
      approved: true
      credit_limit: 50000
    tags: ["vip", "approval"]
  
  - id: "regular_customer" 
    priority: 50
    condition: "credit_score > 650 and annual_income > 50000"
    actions:
      approved: true
      credit_limit: 25000
    tags: ["regular", "approval"]
  
  - id: "high_risk"
    priority: 75
    condition: "previous_defaults > 0 or credit_score < 600"
    actions:
      approved: false
    tags: ["risk", "rejection"]
```


### Execute Rules
```python
from symbolica import Engine, facts

# Load rules
engine = Engine.from_yaml("rules.yaml")

# Define customer data
customer = facts(
    customer_tier="vip",
    credit_score=800,
    annual_income=120000,
    previous_defaults=0
)

# Execute rules
result = engine.reason(customer)

print(f"Approved: {result.verdict['approved']}")
print(f"Credit Limit: ${result.verdict['credit_limit']:,}")
print(f"Execution Time: {result.execution_time_ms:.2f}ms")

print(f"Reasoning: {result.reasoning}")
```

**Output:**
```
Approved: True
Credit Limit: $50,000
Execution Time: 0.15ms
Reasoning: ✓ vip_customer: customer_tier(vip) == 'vip' AND credit_score(800) > 750
```

### LLM Integration

```python
# Get clean context for LLM
llm_context = result.get_llm_context()

prompt = f"""
Customer approval decision:
{llm_context['verdict']}


Reasoning: {llm_context['reasoning']}
Rules fired: {llm_context['fired_rules']}
"""
```

## Advanced Features

### Structured Conditions

For complex logic, use nested conditions:

```yaml
rules:
  - id: "complex_approval"
    condition:
      all:
        - "age >= 18"
        - "income > 50000"
        - any:
          - "credit_score >= 750"
          - all:
            - "credit_score >= 650" 
            - "employment_years >= 2"
        - not: "bankruptcy_history == true"
    actions:
      approved: true
```

### Rule Chaining

Create workflows by triggering other rules automatically:

```yaml
rules:
  - id: "vip_customer"
    priority: 100
    condition: "customer_tier == 'vip' and credit_score > 750"
    actions:
      approved: true
      credit_limit: 50000
    triggers: ["send_welcome_package"]
    
  - id: "regular_customer"
    priority: 50
    condition: "credit_score > 650 and annual_income > 50000"
    actions:
      approved: true
      credit_limit: 25000
    triggers: ["send_approval_email"]
    
  - id: "send_welcome_package"
    priority: 25
    condition: "approved == True and customer_tier == 'vip'"
    actions:
      welcome_package_sent: true
      priority_support: true
    tags: ["notification", "vip"]
  
  - id: "send_approval_email"
    priority: 25
    condition: "approved == True"
    actions:
      email_sent: true
      onboarding_started: true
    tags: ["notification", "approval"]
```

**Output with chaining:**
```
Reasoning: ✓ vip_customer: customer_tier(vip) == 'vip' AND credit_score(800) > 750, set approved=True, credit_limit=50000
✓ send_welcome_package: approved(True) == True and customer_tier(vip) == 'vip', set welcome_package_sent=True, priority_support=True (triggered by vip_customer)
```

### Backward Chaining

Find which rules can achieve your goals:

```python
from symbolica import goal

# What rules can approve a customer?
approval_goal = goal(approved=True)
supporting_rules = engine.find_rules_for_goal(approval_goal)

for rule in supporting_rules:
    print(f"Rule '{rule.id}': {rule.condition}")

# Can this customer get approved?
can_approve = engine.can_achieve_goal(approval_goal, customer)
print(f"Achievable: {can_approve}")
```

**Output:**
```
Rule 'vip_customer': customer_tier == 'vip' and credit_score > 750
Rule 'regular_customer': credit_score > 650 and annual_income > 50000
Achievable: True
```

### Multiple Rule Files

```python
# Load from directory
engine = Engine.from_yaml("rules/")

# Load from multiple files
engine = Engine.from_yaml(["approval.yaml", "pricing.yaml", "notifications.yaml"])
```

### Custom Functions

Extend rules with safe lambda functions for complex business logic:

```python
from symbolica import Engine, facts

# Register custom functions (lambdas are safe by default)
engine = Engine()
engine.register_function("risk_score", lambda credit: "low" if credit > 700 else "high")
engine.register_function("fraud_check", lambda amount, history: amount > history * 3)

# Use in rules
rules_yaml = """
rules:
  - id: approve_loan
    condition: "risk_score(credit_score) == 'low' and fraud_check(amount, avg_transaction) == False"
    actions:
      approved: true
      interest_rate: 0.05
"""

engine = Engine.from_yaml(rules_yaml)
engine.register_function("risk_score", lambda credit: "low" if credit > 700 else "high")
engine.register_function("fraud_check", lambda amount, history: amount > history * 3)

result = engine.reason(facts(credit_score=750, amount=5000, avg_transaction=2000))
print(result.verdict)  # {'approved': True, 'interest_rate': 0.05}
```

**Safety Features:**
- Lambda functions only by default (prevents infinite loops)
- Full functions require explicit `allow_unsafe=True` flag
- Function failures don't crash the rule engine
- Comprehensive input validation

### Temporal Functions

Monitor time-series data and detect patterns over time:

```python
from symbolica import Engine, facts

# Infrastructure monitoring rules
monitoring_rules = """
rules:
  - id: cpu_sustained_high
    condition: "sustained_above('cpu_utilization', 90, 600)"  # >90% for 10 minutes
    actions:
      alert: "CPU sustained high"
      severity: "critical"
      
  - id: memory_trending_up
    condition: "recent_avg('memory_usage', 300) > 85"  # Average >85% in 5 minutes
    actions:
      alert: "Memory trending high"
      severity: "warning"
      
  - id: rate_limit_check
    condition: "recent_count('api_calls', 60) > 100"  # >100 calls in 1 minute
    actions:
      rate_limited: true
      retry_after: 60
"""

engine = Engine.from_yaml(monitoring_rules)

# Feed time-series data
for i in range(20):
    engine.store_datapoint("cpu_utilization", 95.0)  # Sustained high CPU
    engine.store_datapoint("memory_usage", 88.0)     # High memory
    engine.store_datapoint("api_calls", 1)           # API call counter

# Evaluate rules
result = engine.reason(facts())
print(result.verdict)
# Output: {'alert': 'CPU sustained high', 'severity': 'critical', 'rate_limited': True}
```

**Available Temporal Functions:**
- `recent_avg(key, duration)` - Average value in time window
- `recent_max(key, duration)` - Maximum value in time window  
- `recent_min(key, duration)` - Minimum value in time window
- `recent_count(key, duration)` - Count of data points in time window
- `sustained_above(key, threshold, duration)` - Check if value stayed above threshold
- `sustained_below(key, threshold, duration)` - Check if value stayed below threshold
- `ttl_fact(key)` - Get TTL fact (returns None if expired)
- `has_ttl_fact(key)` - Check if TTL fact exists and is valid

**Perfect for:**
- Infrastructure monitoring and alerting
- Session management with TTL
- Rate limiting and throttling
- SLA monitoring and compliance
- Fraud detection patterns

### Performance Testing

```python
import time

# Measure performance
start = time.perf_counter()
for _ in range(1000):
    result = engine.reason(customer)
elapsed = time.perf_counter() - start

print(f"1000 executions: {elapsed*1000:.2f}ms")
print(f"Rate: {1000/elapsed:.0f} executions/second")
```

## Architecture
Symbolica uses a clean, focused architecture:

```
┌─────────────────────────────────────────┐
│              Public API                 │
│     Engine, facts, goal, from_yaml      │
├─────────────────────────────────────────┤
│               Core Models               │
│   Rule, Facts, ExecutionResult, Goal    │
├─────────────────────────────────────────┤
│               Evaluation                │
│    ASTEvaluator, DAGExecutor            │
├─────────────────────────────────────────┤
│            Internal Systems             │
│    YAML Parser, Dependency Analysis     │
└─────────────────────────────────────────┘
```

### Key Components

- **Engine** - Main orchestrator for rule execution
- **ASTEvaluator** - Fast expression evaluation with detailed tracing
- **DAGExecutor** - Dependency-aware rule execution 
- **BackwardChainer** - Reverse search for goal achievement

## API Reference

### Core Classes

```python
from symbolica import Engine, facts, goal

# Create engine
engine = Engine.from_yaml("rules.yaml")          # From file
engine = Engine.from_yaml(yaml_string)           # From string

# Create facts
customer = facts(age=30, income=75000)           # Using helper
customer = {"age": 30, "income": 75000}          # Or plain dict

# Execute rules
result = engine.reason(customer)

# Access results
result.verdict          # Dict of all outputs
result.fired_rules      # List of rule IDs that fired
result.reasoning        # Human-readable explanation
result.execution_time_ms # Performance timing

# Backward chaining
goal_obj = goal(approved=True)
rules = engine.find_rules_for_goal(goal_obj)
achievable = engine.can_achieve_goal(goal_obj, customer)
```

### Rule Structure

```yaml
rules:
  - id: "unique_rule_id"              # Required: unique identifier
    priority: 100                     # Optional: execution order (higher first)
    condition: "expression"           # Required: when to fire
    actions:                          # Required: what to set
      field: value
    triggers: ["other_rule_id"]       # Optional: rules to trigger
    tags: ["category", "type"]        # Optional: metadata
```

## Testing

```python
# Test conditions directly
result = engine.test_condition("credit_score > 650", customer)
print(f"Condition result: {result}")

# Validate rules before deployment
try:
    engine = Engine.from_yaml("rules.yaml")
    print("Rules are valid")
except ValidationError as e:
    print(f"Invalid rules: {e}")
```

## Configuration

```python
# Basic configuration
engine = Engine.from_yaml("rules.yaml")

# Load from directory with pattern
engine = Engine.from_yaml("rules/", pattern="*.yaml")

# Error handling
try:
    result = engine.reason(facts)
except EvaluationError as e:
    print(f"Evaluation failed: {e}")
```
## Examples

Check out the [examples/](examples/) directory:

- **[basic_example.py](examples/basic_example.py)** - Simple customer approval
- **[enhanced_structured_conditions_example.py](examples/enhanced_structured_conditions_example.py)** - Complex nested logic
- **[simple_backward_search_example.py](examples/simple_backward_search_example.py)** - Goal-directed reasoning
- **[custom_functions_example.py](examples/custom_functions_example.py)** - Custom business logic functions
- **[temporal_functions_example.py](examples/temporal_functions_example.py)** - Time-series monitoring and alerting

## Performance

- **Sub-millisecond execution** for typical rule sets
- **6,000+ executions per second** on standard hardware  
- **Linear scaling** up to 1000+ rules
- **Minimal memory footprint**
- **Temporal functions** maintain performance with efficient in-memory time-series storage
- **Custom functions** integrate seamlessly with zero performance impact

## Contributing

1. Fork the repository
2. Create a feature branch  
3. Add tests for new functionality
4. Run tests: `pytest`
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/anibjoshi/symbolica/issues)
- **Documentation**: [Read the Docs](https://symbolica.readthedocs.io)
- **Repository**: [GitHub](https://github.com/anibjoshi/symbolica)

---

**Symbolica**: Reliable reasoning for AI agents. Because deterministic beats probabilistic for critical decisions.