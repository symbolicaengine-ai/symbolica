"""
LangGraph + Symbolica Integration: Intelligent Customer Support Agent

This example demonstrates how to combine LangGraph's stateful conversation management
with Symbolica's rule-based decision making to create an intelligent support agent.

LangGraph handles:
- Conversation state and flow
- Message routing between nodes
- Context management

Symbolica handles:
- Business rules for routing and escalation
- SLA policies and priority assignment
- Automated decision making

Setup:
    pip install langgraph langchain-openai
    export OPENAI_API_KEY="your-key-here"
"""

import os
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import openai
from symbolica import Engine, facts
from symbolica.core.models import Rule

# Define the state that will be passed between nodes
class SupportState(TypedDict):
    """State object that flows through the LangGraph nodes"""
    messages: Annotated[list[BaseMessage], add_messages]
    customer_tier: str
    issue_category: str
    priority: str
    assigned_agent: str
    escalated: bool
    ticket_id: str

class LangGraphSupportAgent:
    """
    Intelligent customer support agent combining LangGraph and Symbolica
    """
    
    def __init__(self):
        # Check for OpenAI API key
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("Please set OPENAI_API_KEY environment variable")
        
        # Initialize LLM for LangGraph
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.1)
        
        # Initialize Symbolica engine with inline support rules
        self.engine = self._create_engine_with_rules()
        
        # Build the LangGraph workflow
        self.workflow = self._build_workflow()
    
    def _create_engine_with_rules(self) -> Engine:
        """Create Symbolica engine with inline rules (workaround for YAML loading issue)"""
        
        engine = Engine(llm_client=openai.OpenAI())
        
        # Define support rules inline
        support_rules = [
            # VIP Critical Escalation
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
            ),
            
            # VIP Standard Priority
            Rule(
                id="vip_standard_priority",
                priority=90,
                condition="customer_tier == 'vip'",
                actions={
                    "priority": "high",
                    "assigned_agent": "vip_specialist",
                    "escalated": False,
                    "response_time_sla": 30
                },
                tags=["vip", "high_priority"]
            ),
            
            # Premium Billing Issue
            Rule(
                id="premium_billing_issue", 
                priority=80,
                condition="customer_tier == 'premium' and issue_category == 'billing'",
                actions={
                    "priority": "high",
                    "assigned_agent": "billing_specialist",
                    "escalated": False,
                    "response_time_sla": 60
                },
                tags=["premium", "billing"]
            ),
            
            # Angry Customer Detection
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
            ),
            
            # Critical System Issue
            Rule(
                id="critical_system_issue",
                priority=100,
                condition="PROMPT('Is this a system outage/critical issue: {message_content}', 'bool') == true",
                actions={
                    "priority": "critical",
                    "assigned_agent": "incident_response",
                    "escalated": True,
                    "notify_engineering": True
                },
                tags=["system", "critical", "incident"]
            ),
            
            # Standard Technical Support
            Rule(
                id="standard_technical_support",
                priority=40,
                condition="customer_tier == 'standard' and issue_category == 'technical'",
                actions={
                    "priority": "medium",
                    "assigned_agent": "general_technical",
                    "escalated": False,
                    "response_time_sla": 240
                },
                tags=["standard", "technical"]
            ),
            
            # Standard Billing Support
            Rule(
                id="standard_billing_support",
                priority=35,
                condition="customer_tier == 'standard' and issue_category == 'billing'",
                actions={
                    "priority": "medium", 
                    "assigned_agent": "general_billing",
                    "escalated": False,
                    "response_time_sla": 180
                },
                tags=["standard", "billing"]
            ),
            
            # Default Routing (Fallback)
            Rule(
                id="default_routing",
                priority=10,
                condition="true",  # Always matches as fallback
                actions={
                    "priority": "medium",
                    "assigned_agent": "general_support",
                    "escalated": False,
                    "response_time_sla": 360
                },
                tags=["default", "fallback"]
            )
        ]
        
        # Add rules to engine
        for rule in support_rules:
            engine.add_rule(rule)
            
        return engine
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow with Symbolica integration"""
        
        # Create the state graph
        workflow = StateGraph(SupportState)
        
        # Add nodes
        workflow.add_node("classify_message", self._classify_message)
        workflow.add_node("apply_business_rules", self._apply_business_rules)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("escalate", self._escalate)
        
        # Define the flow
        workflow.set_entry_point("classify_message")
        
        workflow.add_edge("classify_message", "apply_business_rules")
        
        # Conditional routing based on Symbolica decisions
        workflow.add_conditional_edges(
            "apply_business_rules",
            self._should_escalate,
            {
                "escalate": "escalate",
                "respond": "generate_response"
            }
        )
        
        workflow.add_edge("generate_response", END)
        workflow.add_edge("escalate", "generate_response")
        
        return workflow.compile()
    
    def _classify_message(self, state: SupportState) -> SupportState:
        """Use LangGraph's LLM to classify the incoming message"""
        
        last_message = state["messages"][-1].content
        
        # Use LangGraph's LLM for classification
        classification_prompt = f"""
        Classify this customer support message:
        Message: "{last_message}"
        
        Return only one word for each:
        Category: [technical, billing, general, complaint]
        Urgency: [low, medium, high, critical]
        
        Format: category,urgency
        """
        
        response = self.llm.invoke(classification_prompt)
        classification = response.content.strip().split(',')
        
        # Update state with classification
        state["issue_category"] = classification[0].strip()
        
        return state
    
    def _apply_business_rules(self, state: SupportState) -> SupportState:
        """Use Symbolica to apply business rules and routing logic"""
        
        last_message = state["messages"][-1].content
        
        # Create facts for Symbolica
        support_facts = facts(
            issue_category=state["issue_category"],
            customer_tier=state.get("customer_tier", "standard"),
            message_content=last_message,
            current_time_hour=9,  # Simulate business hours
            queue_length=15,
            is_weekend=False
        )
        
        # Execute Symbolica rules
        result = self.engine.reason(support_facts)
        
        # Update state with Symbolica decisions
        state["priority"] = result.verdict.get("priority", "medium")
        state["assigned_agent"] = result.verdict.get("assigned_agent", "general")
        state["escalated"] = result.verdict.get("escalated", False)
        
        return state
    
    def _should_escalate(self, state: SupportState) -> str:
        """Conditional routing based on Symbolica's escalation decision"""
        return "escalate" if state["escalated"] else "respond"
    
    def _escalate(self, state: SupportState) -> SupportState:
        """Handle escalation process"""
        
        escalation_message = AIMessage(
            content=f"This issue has been escalated to {state['assigned_agent']} "
                   f"with {state['priority']} priority. You will receive a response shortly."
        )
        
        state["messages"].append(escalation_message)
        return state
    
    def _generate_response(self, state: SupportState) -> SupportState:
        """Generate contextual response using LangGraph's LLM"""
        
        # Build context from state and previous messages
        context = f"""
        Customer Tier: {state.get('customer_tier', 'standard')}
        Issue Category: {state['issue_category']}
        Priority: {state['priority']}
        Assigned Agent: {state['assigned_agent']}
        Escalated: {state['escalated']}
        """
        
        conversation_history = "\n".join([
            f"{msg.type}: {msg.content}" for msg in state["messages"][-3:]
        ])
        
        response_prompt = f"""
        You are a helpful customer support agent. Generate a professional response.
        
        Context: {context}
        Recent conversation: {conversation_history}
        
        Provide a helpful, professional response that acknowledges their concern
        and provides next steps based on the priority and assignment.
        """
        
        response = self.llm.invoke(response_prompt)
        
        # Add response to conversation
        state["messages"].append(AIMessage(content=response.content))
        
        return state
    
    def handle_support_request(self, message: str, customer_tier: str = "standard") -> dict:
        """
        Process a customer support request through the LangGraph + Symbolica workflow
        
        Args:
            message: Customer's support request
            customer_tier: Customer's service tier (standard, premium, vip)
            
        Returns:
            Dictionary with response and processing details
        """
        
        # Initialize state
        initial_state = SupportState(
            messages=[HumanMessage(content=message)],
            customer_tier=customer_tier,
            issue_category="",
            priority="",
            assigned_agent="",
            escalated=False,
            ticket_id=f"TKT-{hash(message) % 10000:04d}"
        )
        
        # Run the workflow
        final_state = self.workflow.invoke(initial_state)
        
        # Extract response
        agent_response = final_state["messages"][-1].content
        
        return {
            "response": agent_response,
            "ticket_id": final_state["ticket_id"],
            "priority": final_state["priority"],
            "assigned_agent": final_state["assigned_agent"],
            "escalated": final_state["escalated"],
            "issue_category": final_state["issue_category"]
        }

def main():
    """Demonstrate the LangGraph + Symbolica integration"""
    
    print("LangGraph + Symbolica Customer Support Agent")
    print("=" * 50)
    
    try:
        # Initialize the support agent
        agent = LangGraphSupportAgent()
        
        # Test scenarios
        test_scenarios = [
            {
                "message": "My server has been down for 2 hours and I'm losing money!",
                "customer_tier": "vip",
                "description": "VIP customer with critical issue"
            },
            {
                "message": "I was charged twice for my subscription this month",
                "customer_tier": "premium", 
                "description": "Premium customer billing issue"
            },
            {
                "message": "How do I reset my password?",
                "customer_tier": "standard",
                "description": "Standard customer general inquiry"
            },
            {
                "message": "Your service is terrible and I want a refund immediately!",
                "customer_tier": "standard",
                "description": "Angry customer complaint"
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\nScenario {i}: {scenario['description']}")
            print(f"Customer: {scenario['message']}")
            print(f"Tier: {scenario['customer_tier']}")
            
            # Process through LangGraph + Symbolica workflow
            result = agent.handle_support_request(
                scenario["message"], 
                scenario["customer_tier"]
            )
            
            print(f"\nAgent Response: {result['response']}")
            print(f"Ticket ID: {result['ticket_id']}")
            print(f"Priority: {result['priority']}")
            print(f"Assigned to: {result['assigned_agent']}")
            print(f"Escalated: {result['escalated']}")
            print(f"Category: {result['issue_category']}")
            print("-" * 50)
            
    except ValueError as e:
        print(f"Setup Error: {e}")
        print("\nTo run this example:")
        print("1. Install dependencies: pip install langgraph langchain-openai")
        print("2. Set your OpenAI API key: export OPENAI_API_KEY='your-key'")
        print("3. Run the example: python langgraph_support_agent.py")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 