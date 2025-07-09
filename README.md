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

```python
# Register custom functions
engine.register_function("risk_score", lambda score: 
    "low" if score > 750 else "high" if score < 600 else "medium"
)

# Use in rules
condition: "risk_score(credit_score) == 'low'"
```

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

## Performance

- **Sub-millisecond execution** for typical rule sets
- **6,000+ executions per second** on standard hardware  
- **Linear scaling** up to 1000+ rules
- **Minimal memory footprint**

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
- **Repository**: [GitHub](https://github.com/anibjoshi/symbolica)

---

**Symbolica**: Reliable reasoning for AI agents. Because deterministic beats probabilistic for critical decisions.