# Symbolica Examples Cookbook

This directory contains a comprehensive set of examples demonstrating Symbolica's features, from basic usage to advanced hybrid AI-rule workflows.

## Getting Started

Each example is self-contained in its own directory with:
- `example.py` - The main Python script
- `*.yaml` - Rule definitions
- Clear documentation and explanations

## Example Structure

### 01_basic_rules/
**Foundation: Core Symbolica concepts**
- Loading rules from YAML
- Creating and using facts
- Understanding rule priorities
- Basic rule execution and results

```bash
cd 01_basic_rules && python example.py
```

### 02_custom_functions/
**Business Logic: Extending rules with custom functions**
- Registering lambda functions
- Complex business calculations
- Safe function execution
- Using functions in rule conditions

```bash
cd 02_custom_functions && python example.py
```

### 03_rule_chaining/
**Automation: Building workflows with rule triggers**
- Rule chaining and triggers
- Multi-step process automation
- Workflow analysis and debugging
- Priority-based execution

```bash
cd 03_rule_chaining && python example.py
```

### 04_llm_integration/
**AI-Powered: Hybrid AI-rule decision making**
- PROMPT() function usage
- Type conversion (str, int, bool, float)
- Secure prompt handling
- Customer service automation

```bash
cd 04_llm_integration && python example.py
```

### 05_temporal_functions/
**Monitoring: Time-series analysis and alerting**
- Storing time-series data
- Trend detection and sustained conditions
- Real-time monitoring rules
- Alert generation

```bash
cd 05_temporal_functions && python example.py
```

### 06_backward_chaining/
**Planning: Goal-directed reasoning**
- Finding rules to achieve goals
- Dependency analysis
- Business planning scenarios
- "What-if" analysis

```bash
cd 06_backward_chaining && python example.py
```

### 07_complex_workflows/
**Integration: All features working together**
- Multi-file rule organization
- Hybrid AI-rule workflows
- Comprehensive monitoring
- Production-ready patterns

```bash
cd 07_complex_workflows && python example.py
```

### 08_langgraph_integration/
**Framework Integration: Symbolica + LangGraph for intelligent agents**
- Stateful conversation management with LangGraph
- Business rule execution with Symbolica
- Customer support agent workflow
- Hybrid conversation + rule architecture

```bash
cd 08_langgraph_integration && python langgraph_support_agent.py
```

### 09_complex_conditions/
**Advanced Logic: Sophisticated business rules with ANY/ALL/NOT**
- Nested logical structures with ANY, ALL, NOT operators
- Complex eligibility and approval workflows
- Real-world insurance underwriting scenarios
- Readable condition syntax vs complex boolean expressions

```bash
cd 09_complex_conditions && python example.py
```

## Feature Matrix

| Feature | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 |
|---------|----|----|----|----|----|----|----|----|----|
| Basic Rules | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Custom Functions | - | ✓ | - | - | - | - | ✓ | - | - |
| Rule Chaining | - | - | ✓ | - | - | - | ✓ | - | - |
| LLM Integration | - | - | - | ✓ | - | - | ✓ | ✓ | - |
| Temporal Functions | - | - | - | - | ✓ | - | ✓ | - | - |
| Backward Chaining | - | - | - | - | - | ✓ | ✓ | - | - |
| Multi-file Rules | - | - | - | - | - | - | ✓ | - | - |
| LangGraph Integration | - | - | - | - | - | - | - | ✓ | - |
| Complex Conditions | - | - | - | - | - | - | - | - | ✓ |

## Running All Examples

```bash
# Run each example in sequence
for dir in 01_basic_rules 02_custom_functions 03_rule_chaining 04_llm_integration 05_temporal_functions 06_backward_chaining 07_complex_workflows 09_complex_conditions; do
    echo "Running $dir..."
    cd $dir && python example.py && cd ..
    echo "---"
done

# Run LangGraph integration example separately (requires additional dependencies)
cd 08_langgraph_integration && python langgraph_support_agent.py
```

## Key Concepts Demonstrated

### Basic Rule Engine Concepts
- **Facts**: Input data for rule evaluation
- **Rules**: Conditions and actions that define business logic
- **Priority**: Execution order for rules
- **Actions**: What happens when a rule fires
- **Reasoning**: Explanation of which rules fired and why

### Advanced Features
- **PROMPT() Function**: Integrate LLM reasoning into rules
- **Custom Functions**: Extend rules with Python business logic
- **Rule Triggers**: Chain rules together for workflows
- **Temporal Functions**: Analyze time-series data and trends
- **Backward Chaining**: Find paths to achieve specific goals
- **Complex Conditions**: Sophisticated logical structures with ANY/ALL/NOT

### Production Patterns
- **Multi-file Organization**: Split complex rule sets across files
- **Monitoring and Alerting**: Built-in system health monitoring
- **Error Handling**: Graceful failure and fallback strategies
- **Performance Optimization**: Efficient rule execution

## LLM Integration Setup

Examples 04, 07, and 08 use real OpenAI API integration. Before running these examples:

1. **Install OpenAI library:**
   ```bash
   pip install openai
   ```

2. **For LangGraph integration (example 08), also install:**
   ```bash
   pip install langgraph langchain-openai
   ```

3. **Set your API key:**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

4. **Run the examples:**
   ```bash
   cd 04_llm_integration && python example.py
   cd 07_complex_workflows && python example.py
   cd 08_langgraph_integration && python langgraph_support_agent.py
   ```

**Note:** These examples will make real API calls to OpenAI and will incur costs. The prompts are designed to be efficient and typically use only a few tokens per call.

## Dependencies

Basic examples (01-03, 05-06, 09):
- Python 3.8+
- symbolica

LLM examples (04, 07):  
- Python 3.8+
- symbolica
- openai
- Valid OpenAI API key (set as OPENAI_API_KEY environment variable)

LangGraph integration (08):
- Python 3.8+
- symbolica
- openai
- langgraph
- langchain-openai
- Valid OpenAI API key (set as OPENAI_API_KEY environment variable)

## Best Practices Demonstrated

1. **Start Simple**: Begin with basic rules before adding complexity
2. **Organize Rules**: Use multiple files for large rule sets
3. **Test Scenarios**: Create comprehensive test cases
4. **Monitor Performance**: Include monitoring and alerting
5. **Document Logic**: Clear rule names and comprehensive explanations
6. **Handle Errors**: Graceful failure handling and fallbacks

## Learning Path

1. **Start with 01_basic_rules** to understand fundamentals
2. **Progress through 02-06** to learn individual features
3. **Study 07_complex_workflows** to see integration patterns
4. **Explore 08_langgraph_integration** for framework integration
5. **Master 09_complex_conditions** for sophisticated business logic
6. **Adapt patterns** to your specific use cases

Each example builds on previous concepts while introducing new capabilities, creating a comprehensive learning experience for Symbolica development. 