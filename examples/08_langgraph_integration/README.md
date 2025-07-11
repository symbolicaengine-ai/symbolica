# LangGraph + Symbolica Integration

This example demonstrates how to combine **LangGraph** for stateful conversation management with **Symbolica** for business rule execution to create an intelligent customer support agent.

## Architecture

```
Customer Message → LangGraph State Management → Symbolica Business Rules → LLM Response Generation
                    │                          │                         │
                    ├─ Conversation Flow       ├─ Routing Logic         ├─ Contextual Responses  
                    ├─ State Tracking          ├─ Escalation Rules      ├─ Professional Tone
                    └─ Node Coordination       └─ Priority Assignment   └─ Next Steps
```

## What This Example Shows

### LangGraph Responsibilities
- **Stateful conversation flow** - Manages multi-turn conversations
- **Node coordination** - Routes between classification, rules, and response nodes
- **Context management** - Maintains conversation history and state
- **Conditional routing** - Directs flow based on Symbolica decisions

### Symbolica Responsibilities  
- **Business rules** - Customer tier routing, SLA policies, escalation triggers
- **AI-enhanced decisions** - Uses PROMPT() for sentiment analysis and urgency detection
- **Priority assignment** - Determines priority based on customer tier and issue type
- **Agent routing** - Assigns appropriate specialist based on issue category

### Key Integration Points
1. **State Flow**: LangGraph manages conversation state, Symbolica processes business logic
2. **Decision Making**: Symbolica rules determine escalation and routing within LangGraph flow
3. **AI Enhancement**: Both systems use LLM calls - LangGraph for conversation, Symbolica for rule evaluation
4. **Conditional Routing**: LangGraph flow branches based on Symbolica's business rule outcomes

## Setup

```bash
# Install dependencies
pip install langgraph langchain-openai symbolica openai

# Set API key
export OPENAI_API_KEY="your-openai-api-key"
```

## Files

- `langgraph_support_agent.py` - Main integration showing LangGraph + Symbolica workflow with inline rules
- `support_rules.yaml` - Reference YAML format (example uses inline rules for simplicity)

## Running the Example

```bash
cd examples/08_langgraph_integration
python langgraph_support_agent.py
```

## Sample Output

```
LangGraph + Symbolica Customer Support Agent
==================================================

Scenario 1: VIP customer with critical issue
Customer: My server has been down for 2 hours and I'm losing money!
Tier: vip

Agent Response: I understand this is a critical situation affecting your business operations. 
As a VIP customer experiencing a server outage, I've immediately escalated your case to our 
senior specialist team with critical priority. Your ticket TKT-7432 has been assigned to our 
incident response team who will contact you within 15 minutes with a resolution plan.

Ticket ID: TKT-7432
Priority: critical
Assigned to: senior_specialist
Escalated: True
Category: technical
--------------------------------------------------

Scenario 2: Premium customer billing issue
Customer: I was charged twice for my subscription this month
Tier: premium

Agent Response: I apologize for the billing error on your premium account. I've assigned your 
case TKT-8951 to our billing specialist team with high priority. As a premium customer, you 
can expect a response and resolution within 60 minutes. We'll investigate the duplicate charge 
and process any necessary refunds immediately.

Ticket ID: TKT-8951
Priority: high
Assigned to: billing_specialist
Escalated: False
Category: billing
--------------------------------------------------
```

## Key Features Demonstrated

### 1. Intelligent Routing
- **Customer tier-based routing** - VIP customers get immediate escalation
- **Issue category detection** - LangGraph classifies, Symbolica routes appropriately
- **Sentiment-based priority** - Angry customers automatically escalated

### 2. Hybrid Decision Making
- **LangGraph flow control** - Manages conversation state and node transitions
- **Symbolica business logic** - Applies company policies and routing rules
- **LLM enhancement** - Both systems use AI for intelligent analysis

### 3. State Management
- **Conversation tracking** - Full message history maintained
- **Business context** - Customer tier, priority, assignment tracked
- **Decision audit trail** - Complete record of routing decisions

### 4. Real-World Business Rules
- **SLA enforcement** - Different response times by customer tier
- **Escalation triggers** - Critical issues and angry customers escalated
- **Capacity management** - Queue length affects routing decisions
- **Business hours handling** - After-hours routing to different teams

## Rule Examples

The example uses inline Symbolica rules for simplicity. Here are some key rules:

### VIP Critical Escalation
```python
Rule(
    id="vip_critical_escalation",
    priority=100,
    condition="customer_tier == 'vip' and PROMPT('Rate urgency 1-10: {message_content}', 'int') >= 8",
    actions={
        "priority": "critical",
        "assigned_agent": "senior_specialist",
        "escalated": True,
        "response_time_sla": 15
    },
    tags=["vip", "critical", "escalation"]
)
```

### AI-Enhanced Sentiment Detection
```python
Rule(
    id="angry_customer_detection",
    priority=95,
    condition="PROMPT('Is customer angry/frustrated in: {message_content}', 'bool') == true",
    actions={
        "priority": "high",
        "assigned_agent": "escalation_specialist",
        "escalated": True,
        "requires_manager_review": True
    },
    tags=["complaint", "escalation", "customer_satisfaction"]
)
```

## Benefits of This Architecture

### For Development Teams
- **Clear separation of concerns** - Conversation flow vs business logic
- **Testable components** - Rules can be tested independently
- **Maintainable policies** - Business rules as code objects
- **Scalable architecture** - Add new rules without workflow changes

### For Business Operations  
- **Consistent routing** - Deterministic customer experience
- **Audit trail** - Complete record of decisions and escalations
- **Policy enforcement** - SLA and tier policies automatically applied
- **Performance monitoring** - Track response times and escalation rates

### For Customer Experience
- **Intelligent routing** - Right specialist for each issue type
- **Priority handling** - Critical issues get immediate attention
- **Context awareness** - Responses consider customer tier and history
- **Professional service** - Consistent, policy-driven interactions

## Extending This Example

### Add New Business Rules
```python
Rule(
    id="weekend_priority_boost",
    priority=85,
    condition="is_weekend == true and customer_tier == 'premium'",
    actions={
        "priority": "high",
        "weekend_premium_handling": True
    },
    tags=["weekend", "premium"]
)
```

### Add New LangGraph Nodes
```python
workflow.add_node("send_notification", self._send_notification)
workflow.add_node("update_crm", self._update_crm)
```

### Integration with External Systems
- **CRM integration** - Update customer records with support interactions
- **Notification systems** - Send alerts based on escalation rules
- **Analytics platforms** - Track support metrics and rule effectiveness

## Why Inline Rules?

This example uses inline Symbolica rules (Rule objects) instead of external YAML files for several reasons:

1. **Self-contained** - Everything needed is in one file
2. **Type safety** - IDE support and validation
3. **Easy debugging** - Step through rule creation
4. **Demonstration clarity** - Rules visible alongside usage
5. **Production flexibility** - Can easily switch to external files or databases

For production use, you might prefer external YAML files or database-stored rules for easier business user management.

This example shows how LangGraph and Symbolica complement each other perfectly - LangGraph for intelligent conversation management and Symbolica for reliable business rule execution. 