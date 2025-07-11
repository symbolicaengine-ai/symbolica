# Symbolica: Deterministic Rule Engine for AI Agents

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Performance](https://img.shields.io/badge/performance-sub--millisecond-brightgreen.svg)](https://github.com/anibjoshi/symbolica)


**Symbolica** is a hybrid rule engine that combines deterministic logic with LLM intelligence. Get the reliability of rule-based systems with the flexibility of AI reasoning.

## Why Symbolica?

AI agents need **deterministic logic** for critical decisions, but also **flexible reasoning** for complex scenarios. Symbolica gives you both:

- **Deterministic rules** for business logic, compliance, and critical decisions
- **LLM integration** for natural language processing, sentiment analysis, and complex reasoning
- **Hybrid workflows** that combine rule-based precision with AI flexibility

**Perfect for:**
- **AI Agent Decision Making** - Combine reliable rules with intelligent reasoning
- **Business Logic** - Customer approval, pricing, risk assessment with AI insights
- **Workflow Automation** - Multi-step processes with rule chaining and LLM evaluation
- **Compliance** - Policy enforcement with audit trails and intelligent analysis

## Key Features

- **Sub-millisecond execution** - 6,000+ executions per second
- **LLM Integration** - Built-in PROMPT() function with security hardening
- **Hybrid AI-Rule workflows** - Combine deterministic rules with LLM reasoning
- **Custom functions** - Extend rules with safe lambda functions for complex business logic
- **Temporal functions** - Time-series analysis and pattern detection for monitoring & alerting
- **Clean explanations** - Perfect for LLM integration and human review
- **Rule chaining** - Create workflows by triggering rules
- **Backward chaining** - Find which rules can achieve goals
- **Flexible syntax** - Simple strings or nested logical structures
- **Security hardening** - Built-in prompt injection protection and input sanitization
- **Zero dependencies** - Just PyYAML (OpenAI client optional for LLM features)

## Installation

```bash
pip install symbolica

# For LLM features (optional)
pip install openai
```

## Quick Start

### Basic Rules
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

## LLM Integration

Symbolica includes built-in LLM integration with security hardening:

### Basic LLM Usage

```python
import openai
from symbolica import Engine, facts

# Set up your LLM client
client = openai.OpenAI(api_key="your-api-key")

# Rules with LLM reasoning
rules_yaml = """
rules:
  - id: sentiment_approval
    priority: 100
    condition: "PROMPT('Analyze sentiment of: {feedback}') == 'positive'"
    actions:
      approved: true
      reason: sentiment_positive
      
  - id: urgency_routing
    priority: 90
    condition: "PROMPT('Is this urgent: {message}', 'bool') == true"
    actions:
      priority: high
      route_to: emergency_team
      
  - id: risk_assessment
    priority: 80
    condition: "PROMPT('Rate risk 1-10: {description}', 'int') > 7"
    actions:
      high_risk: true
      requires_review: true
"""

# Create engine with LLM client
engine = Engine.from_yaml(rules_yaml, llm_client=client)

# Execute with LLM reasoning
result = engine.reason(facts(
    feedback="I absolutely love this product!",
    message="Server is completely down, customers can't access anything",
    description="First-time customer with no credit history requesting large loan"
))

print(result.verdict)
# Output: {'approved': True, 'reason': 'sentiment_positive', 'priority': 'high', 'route_to': 'emergency_team', 'high_risk': True, 'requires_review': True}
```

### PROMPT() Function

The `PROMPT()` function provides secure LLM integration:

```python
# Basic usage
PROMPT("Analyze this text: {user_input}")                    # Returns string
PROMPT("Rate confidence 1-10: {scenario}", "int")            # Returns integer  
PROMPT("Is this urgent: {message}", "bool")                  # Returns boolean
PROMPT("Calculate score: {data}", "float")                   # Returns float
PROMPT("Summarize in 50 words: {content}", "str", 100)       # With max_tokens
```

**Security Features:**
- **Prompt injection protection** - Automatically detects and sanitizes malicious inputs
- **Input validation** - Sanitizes variables before template substitution
- **Output validation** - Validates and converts LLM responses to expected types
- **Audit logging** - Comprehensive logging of all LLM interactions
- **Rate limiting safe** - Designed for production use

### Hybrid AI-Rule Workflows

Combine deterministic rules with AI reasoning:

```python
hybrid_rules = """
rules:
  - id: ai_content_analysis
    priority: 100
    condition: "PROMPT('Classify content: {text}') == 'appropriate'"
    actions:
      content_approved: true
      ai_classification: "{{ PROMPT('Categorize: {text}') }}"
      
  - id: rule_based_limits
    priority: 90
    condition: "content_approved == true and word_count < 1000"
    actions:
      final_approval: true
      
  - id: human_review_needed
    priority: 80
    condition: "PROMPT('Rate complexity 1-10: {text}', 'int') > 8"
    actions:
      requires_human_review: true
      complexity_score: "{{ LAST_PROMPT_RESULT }}"
"""

engine = Engine.from_yaml(hybrid_rules, llm_client=client)
result = engine.reason(facts(text="Complex technical analysis...", word_count=750))
```

### LLM Integration Examples

```python
# Customer service routing
customer_service_rules = """
rules:
  - id: angry_customer
    condition: "PROMPT('Detect emotion: {message}') == 'angry'"
    actions:
      priority: urgent
      route_to: senior_agent
      
  - id: technical_issue
    condition: "PROMPT('Is this technical: {message}', 'bool') == true"
    actions:
      department: technical_support
      estimated_time: 30
      
  - id: billing_inquiry
    condition: "PROMPT('Categorize: {message}') == 'billing'"
    actions:
      department: billing
      auto_response: "{{ PROMPT('Generate billing response for: {message}') }}"
"""

# Content moderation
moderation_rules = """
rules:
  - id: inappropriate_content
    condition: "PROMPT('Is this appropriate: {content}', 'bool') == false"
    actions:
      blocked: true
      reason: "{{ PROMPT('Why inappropriate: {content}') }}"
      
  - id: spam_detection
    condition: "PROMPT('Rate spam likelihood 1-10: {content}', 'int') > 7"
    actions:
      spam_score: "{{ LAST_PROMPT_RESULT }}"
      requires_review: true
"""

# Financial analysis
financial_rules = """
rules:
  - id: market_sentiment
    condition: "PROMPT('Analyze market sentiment: {news}') == 'positive'"
    actions:
      sentiment: bullish
      confidence: "{{ PROMPT('Rate confidence 1-10: {news}', 'int') }}"
      
  - id: risk_analysis
    condition: "PROMPT('Calculate risk score 1-100: {portfolio}', 'int') > 75"
    actions:
      high_risk: true
      recommendation: "{{ PROMPT('Suggest action for high risk: {portfolio}') }}"
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
    triggers: ["send_welcome_package", "assign_personal_banker"]
    
  - id: "send_welcome_package"
    priority: 25
    condition: "approved == True and customer_tier == 'vip'"
    actions:
      welcome_package_sent: true
      message: "{{ PROMPT('Generate VIP welcome message for {customer_name}') }}"
    tags: ["notification", "vip"]
  
  - id: "assign_personal_banker"
    priority: 25
    condition: "approved == True and credit_limit >= 50000"
    actions:
      personal_banker: true
      banker_name: "{{ PROMPT('Assign best banker for VIP client profile: {customer_profile}') }}"
    tags: ["assignment", "vip"]
```

**Output with LLM-enhanced chaining:**
```
Reasoning: ✓ vip_customer: customer_tier(vip) == 'vip' AND credit_score(800) > 750, set approved=True, credit_limit=50000
✓ send_welcome_package: approved(True) == True and customer_tier(vip) == 'vip', set welcome_package_sent=True, message="Welcome to our VIP program, valued customer!" (triggered by vip_customer)
✓ assign_personal_banker: approved(True) == True and credit_limit(50000) >= 50000, set personal_banker=True, banker_name="Sarah Johnson - Senior Wealth Advisor" (triggered by vip_customer)
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

### Multiple Rule Files

```python
# Load from directory
engine = Engine.from_yaml("rules/", llm_client=client)

# Load from multiple files
engine = Engine.from_yaml(["approval.yaml", "ai_analysis.yaml", "notifications.yaml"], llm_client=client)
```

### Custom Functions

Extend rules with safe lambda functions for complex business logic:

```python
from symbolica import Engine, facts

# Register custom functions (lambdas are safe by default)
engine = Engine()
engine.register_function("risk_score", lambda credit: "low" if credit > 700 else "high")
engine.register_function("fraud_check", lambda amount, history: amount > history * 3)

# Use in rules with LLM integration
rules_yaml = """
rules:
  - id: approve_loan
    condition: "risk_score(credit_score) == 'low' and fraud_check(amount, avg_transaction) == False"
    actions:
      approved: true
      interest_rate: 0.05
      explanation: "{{ PROMPT('Explain loan approval for {customer_name} with {credit_score} credit score') }}"
"""

engine = Engine.from_yaml(rules_yaml, llm_client=client)
engine.register_function("risk_score", lambda credit: "low" if credit > 700 else "high")
engine.register_function("fraud_check", lambda amount, history: amount > history * 3)

result = engine.reason(facts(
    credit_score=750, 
    amount=5000, 
    avg_transaction=2000,
    customer_name="John Smith"
))
print(result.verdict)  
# {'approved': True, 'interest_rate': 0.05, 'explanation': 'Loan approved for John Smith based on excellent credit score of 750, indicating low risk profile.'}
```

### Temporal Functions

Monitor time-series data and detect patterns over time:

```python
from symbolica import Engine, facts

# Infrastructure monitoring rules with AI analysis
monitoring_rules = """
rules:
  - id: cpu_sustained_high
    condition: "sustained_above('cpu_utilization', 90, 600)"  # >90% for 10 minutes
    actions:
      alert: "CPU sustained high"
      severity: "critical"
      analysis: "{{ PROMPT('Analyze CPU pattern: sustained >90% for 10min') }}"
      
  - id: anomaly_detection
    condition: "recent_avg('response_time', 300) > 2000"  # Average >2s in 5 minutes
    actions:
      alert: "Performance anomaly"
      severity: "warning"
      recommendation: "{{ PROMPT('Suggest fix for high response times: {recent_events}') }}"
      
  - id: intelligent_capacity_planning
    condition: "PROMPT('Predict if system needs scaling based on: {metrics}', 'bool') == true"
    actions:
      scale_recommended: true
      scaling_plan: "{{ PROMPT('Create scaling plan for: {metrics}') }}"
"""

engine = Engine.from_yaml(monitoring_rules, llm_client=client)

# Feed time-series data
for i in range(20):
    engine.store_datapoint("cpu_utilization", 95.0)  # Sustained high CPU
    engine.store_datapoint("response_time", 2500.0)  # High response time

# Evaluate with AI analysis
result = engine.reason(facts(
    metrics="CPU: 95%, Memory: 80%, Response: 2.5s",
    recent_events="High traffic from marketing campaign"
))
print(result.verdict)
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

## Performance Testing

```python
import time

# Measure performance (including LLM calls)
start = time.perf_counter()
for _ in range(100):  # Reduced for LLM testing
    result = engine.reason(customer)
elapsed = time.perf_counter() - start

print(f"100 executions: {elapsed*1000:.2f}ms")
print(f"Rate: {100/elapsed:.0f} executions/second")
```

## Architecture
Symbolica uses a clean, focused architecture with optional LLM integration:

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
│            LLM Integration              │
│   PromptEvaluator, SecurityHardening    │
├─────────────────────────────────────────┤
│            Internal Systems             │
│    YAML Parser, Dependency Analysis     │
└─────────────────────────────────────────┘
```

### Key Components

- **Engine** - Main orchestrator for rule execution with optional LLM client
- **ASTEvaluator** - Fast expression evaluation with PROMPT() function support
- **DAGExecutor** - Dependency-aware rule execution 
- **BackwardChainer** - Reverse search for goal achievement
- **PromptEvaluator** - Secure LLM integration with hardening
- **TemporalStore** - Time-series data management for temporal functions

## API Reference

### Core Classes

```python
from symbolica import Engine, facts, goal
import openai

# Create engine
engine = Engine.from_yaml("rules.yaml")                    # Basic engine
engine = Engine.from_yaml("rules.yaml", llm_client=client) # With LLM integration

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

# LLM integration
result = engine.reason(facts(message="Urgent issue needs attention"))
# PROMPT() functions in rules will be evaluated automatically
```

### Rule Structure

```yaml
rules:
  - id: "unique_rule_id"              # Required: unique identifier
    priority: 100                     # Optional: execution order (higher first)
    condition: "expression"           # Required: when to fire (can include PROMPT())
    actions:                          # Required: what to set
      field: value
      ai_field: "{{ PROMPT('Generate response') }}"  # LLM-generated values
    triggers: ["other_rule_id"]       # Optional: rules to trigger
    tags: ["category", "type"]        # Optional: metadata
```

### PROMPT() Function Reference

```python
# Basic syntax
PROMPT("template_string")                           # Returns string
PROMPT("template_string", "return_type")            # With type conversion
PROMPT("template_string", "return_type", max_tokens) # With token limit

# Return types
"str"    # String (default)
"int"    # Integer  
"float"  # Float
"bool"   # Boolean

# Template variables
PROMPT("Analyze sentiment of: {user_message}")     # Uses facts
PROMPT("Rate {product} on scale 1-10", "int")      # Variable substitution

# In actions (template expressions)
actions:
  summary: "{{ PROMPT('Summarize: {content}') }}"
  score: "{{ PROMPT('Rate 1-10: {item}', 'int') }}"
  
# Special variables
actions:
  last_result: "{{ LAST_PROMPT_RESULT }}"          # Result of last PROMPT() call
```

## Testing

```python
# Test conditions directly (including LLM)
result = engine.test_condition("PROMPT('Classify: {text}') == 'positive'", facts(text="Great product!"))
print(f"Condition result: {result}")

# Validate rules before deployment
try:
    engine = Engine.from_yaml("rules.yaml", llm_client=client)
    print("Rules are valid")
except ValidationError as e:
    print(f"Invalid rules: {e}")
```

## Configuration

```python
# Basic configuration
engine = Engine.from_yaml("rules.yaml")

# With LLM client
import openai
client = openai.OpenAI(api_key="your-key")
engine = Engine.from_yaml("rules.yaml", llm_client=client)

# Load from directory with pattern
engine = Engine.from_yaml("rules/", pattern="*.yaml", llm_client=client)

# Error handling
try:
    result = engine.reason(facts)
except EvaluationError as e:
    print(f"Evaluation failed: {e}")
```

## Examples

Check out the [examples/](examples/) directory for a comprehensive cookbook with progressive learning:

- **[01_basic_rules/](examples/01_basic_rules/)** - Foundation: Core Symbolica concepts
- **[02_custom_functions/](examples/02_custom_functions/)** - Business Logic: Extending rules with custom functions  
- **[03_rule_chaining/](examples/03_rule_chaining/)** - Automation: Building workflows with rule triggers
- **[04_llm_integration/](examples/04_llm_integration/)** - AI-Powered: Hybrid AI-rule decision making
- **[05_temporal_functions/](examples/05_temporal_functions/)** - Monitoring: Time-series analysis and alerting
- **[06_backward_chaining/](examples/06_backward_chaining/)** - Planning: Goal-directed reasoning
- **[07_complex_workflows/](examples/07_complex_workflows/)** - Integration: All features working together

Each example is self-contained with clear documentation and real-world use cases. See the [examples README](examples/README.md) for detailed setup instructions and feature matrix.

## Performance

- **Sub-millisecond execution** for rule-only evaluations
- **Intelligent LLM caching** minimizes API calls
- **6,000+ executions per second** for pure rule logic
- **Linear scaling** up to 1000+ rules
- **Minimal memory footprint**
- **Temporal functions** maintain performance with efficient in-memory time-series storage
- **Custom functions** integrate seamlessly with zero performance impact
- **LLM calls** are optimized with request deduplication and smart batching

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

**Symbolica**: Hybrid AI-Rule reasoning for intelligent agents. Combine the reliability of deterministic rules with the flexibility of LLM intelligence.