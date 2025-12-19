#!/usr/bin/env python3
"""
LangGraph + Machine Rules Integration Example

This example demonstrates how to integrate the Machine Rules Engine
with LangGraph to create AI agent workflows that use rule-based decision making.

The example shows:
1. Creating a customer service agent with rule-based routing
2. Using rules to determine conversation flow and responses
3. Combining LLM reasoning with deterministic rule execution
4. Building a stateful conversation agent with rules

Requirements:
    pip install langgraph langchain-ollama

    # Ensure Ollama is running with the model:
    ollama pull gpt-oss:20b
"""

import os
import tempfile
from typing import Dict, Any, List, TypedDict, Optional, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_ollama import ChatOllama

# Machine Rules imports
from machine_rules.api.registry import RuleServiceProviderManager
from machine_rules.api.execution_set import Rule, RuleExecutionSet
from machine_rules.loader.yaml_loader import YAMLRuleLoader


class ConversationState(TypedDict):
    """State for our LangGraph conversation agent."""

    messages: List[BaseMessage]
    customer_data: Dict[str, Any]
    conversation_context: Dict[str, Any]
    rule_results: List[Dict[str, Any]]
    next_action: str


class RulesLangGraphAgent:
    """
    A LangGraph agent that uses Machine Rules for decision making.
    """

    def __init__(self):
        """Initialize the agent with rule engine and LangGraph workflow."""
        # Initialize Ollama LLM
        self.llm = ChatOllama(
            model="gpt-oss:20b",
            temperature=0.7,
        )

        # Initialize rules engine
        self.provider = RuleServiceProviderManager.get("api")
        if not self.provider:
            raise RuntimeError("Rules engine not initialized")

        self.admin = self.provider.get_rule_administrator()
        self.runtime = self.provider.get_rule_runtime()

        # Setup rules and workflow
        self._setup_customer_service_rules()
        self._setup_escalation_rules()
        self._setup_workflow()

    def _setup_customer_service_rules(self):
        """Setup customer service routing and response rules."""

        # Customer tier classification rules
        tier_rules_yaml = """
name: "customer_tier_rules"
description: "Rules for classifying customer tiers and priorities"
rules:
  - name: "vip_customer"
    condition: >
      fact.get('total_spent', 0) > 10000 or
      fact.get('account_type') == 'premium'
    action: >
      {
        'tier': 'VIP',
        'priority': 'high',
        'agent_type': 'senior',
        'response_time_sla': 5,
        'greeting': 'Thank you for being a valued VIP customer!'
      }
    priority: 100

  - name: "loyal_customer"
    condition: >
      fact.get('years_customer', 0) > 2 or
      fact.get('total_spent', 0) > 1000
    action: >
      {
        'tier': 'Loyal',
        'priority': 'medium',
        'agent_type': 'standard',
        'response_time_sla': 15,
        'greeting': 'Thank you for your continued loyalty!'
      }
    priority: 50

  - name: "new_customer"
    condition: "True"
    action: >
      {
        'tier': 'Standard',
        'priority': 'standard',
        'agent_type': 'junior',
        'response_time_sla': 30,
        'greeting': 'Welcome! How can we help you today?'
      }
    priority: 1
"""

        # Create and register tier rules
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(tier_rules_yaml)
            tier_path = f.name

        try:
            tier_execution_set = YAMLRuleLoader.from_file(tier_path)
            self.admin.register_rule_execution_set("customer_tiers", tier_execution_set)
        finally:
            os.unlink(tier_path)

    def _setup_escalation_rules(self):
        """Setup escalation and routing rules."""

        escalation_rules = [
            Rule(
                name="urgent_escalation",
                condition=lambda fact: (
                    any(
                        keyword in fact.get("message", "").lower()
                        for keyword in [
                            "urgent",
                            "emergency",
                            "critical",
                            "down",
                            "broken",
                        ]
                    )
                    or fact.get("sentiment_score", 0.5) < 0.2
                ),
                action=lambda fact: {
                    "escalate": True,
                    "escalation_level": "urgent",
                    "route_to": "supervisor",
                    "reason": "urgent_keywords_or_negative_sentiment",
                },
                priority=100,
            ),
            Rule(
                name="technical_issue",
                condition=lambda fact: any(
                    keyword in fact.get("message", "").lower()
                    for keyword in ["technical", "bug", "error", "not working", "crash"]
                ),
                action=lambda fact: {
                    "escalate": False,
                    "route_to": "technical_support",
                    "suggested_response": "technical_troubleshooting",
                },
                priority=75,
            ),
            Rule(
                name="billing_issue",
                condition=lambda fact: any(
                    keyword in fact.get("message", "").lower()
                    for keyword in ["billing", "charge", "payment", "refund", "invoice"]
                ),
                action=lambda fact: {
                    "escalate": False,
                    "route_to": "billing_team",
                    "suggested_response": "billing_assistance",
                },
                priority=75,
            ),
            Rule(
                name="general_inquiry",
                condition=lambda fact: True,
                action=lambda fact: {
                    "escalate": False,
                    "route_to": "general_support",
                    "suggested_response": "general_assistance",
                },
                priority=1,
            ),
        ]

        escalation_set = RuleExecutionSet(
            name="escalation_rules", rules=escalation_rules
        )
        self.admin.register_rule_execution_set("escalation", escalation_set)

    def _setup_workflow(self):
        """Setup the LangGraph workflow."""
        workflow = StateGraph(ConversationState)

        # Add nodes
        workflow.add_node("analyze_customer", self._analyze_customer)
        workflow.add_node("apply_tier_rules", self._apply_tier_rules)
        workflow.add_node("apply_routing_rules", self._apply_routing_rules)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("escalate", self._escalate)

        # Add edges (LangGraph v1 uses START instead of set_entry_point)
        workflow.add_edge(START, "analyze_customer")
        workflow.add_edge("analyze_customer", "apply_tier_rules")
        workflow.add_edge("apply_tier_rules", "apply_routing_rules")
        workflow.add_conditional_edges(
            "apply_routing_rules",
            self._should_escalate,
        )
        workflow.add_edge("generate_response", END)
        workflow.add_edge("escalate", END)

        self.workflow = workflow.compile()

    def _analyze_customer(self, state: ConversationState) -> ConversationState:
        """Analyze customer data and message context."""
        latest_message = state["messages"][-1]

        # Extract customer context (in real app, this would come from CRM/database)
        customer_data = state.get(
            "customer_data",
            {
                "customer_id": "12345",
                "total_spent": 5000,
                "years_customer": 3,
                "account_type": "standard",
                "previous_issues": 2,
            },
        )

        # Analyze message sentiment (simplified - use proper sentiment analysis)
        message_text = str(latest_message.content).lower()
        sentiment_score = 0.8  # Default positive
        if any(
            word in message_text
            for word in ["angry", "frustrated", "terrible", "awful"]
        ):
            sentiment_score = 0.2
        elif any(word in message_text for word in ["urgent", "critical", "emergency"]):
            sentiment_score = 0.3

        conversation_context = {
            "message": str(latest_message.content),
            "sentiment_score": sentiment_score,
            "message_length": len(str(latest_message.content)),
            "is_first_message": len(state["messages"]) == 1,
        }

        return {
            **state,
            "customer_data": customer_data,
            "conversation_context": conversation_context,
        }

    def _apply_tier_rules(self, state: ConversationState) -> ConversationState:
        """Apply customer tier classification rules."""
        session = self.runtime.create_rule_session("customer_tiers")
        session.add_facts([state["customer_data"]])
        tier_results = session.execute()
        session.close()

        # Get the highest priority tier result
        tier_info = (
            tier_results[0]
            if tier_results
            else {"tier": "Standard", "priority": "standard"}
        )

        return {
            **state,
            "rule_results": [{"type": "tier_classification", "result": tier_info}],
        }

    def _apply_routing_rules(self, state: ConversationState) -> ConversationState:
        """Apply routing and escalation rules."""
        # Combine customer data and conversation context for rule evaluation
        fact = {**state["customer_data"], **state["conversation_context"]}

        session = self.runtime.create_rule_session("escalation")
        session.add_facts([fact])
        routing_results = session.execute()
        session.close()

        # Get the highest priority routing result
        routing_info = (
            routing_results[0]
            if routing_results
            else {"escalate": False, "route_to": "general_support"}
        )

        state["rule_results"].append(
            {"type": "routing_decision", "result": routing_info}
        )

        return {
            **state,
            "next_action": "escalate" if routing_info.get("escalate") else "respond",
        }

    def _should_escalate(
        self, state: ConversationState
    ) -> Literal["escalate", "generate_response"]:
        """Conditional edge function to determine if escalation is needed."""
        action = state.get("next_action", "respond")
        if action == "escalate":
            return "escalate"
        return "generate_response"

    def _generate_response(self, state: ConversationState) -> ConversationState:
        """Generate an appropriate response based on rules results using LLM."""
        tier_result = next(
            (
                r["result"]
                for r in state["rule_results"]
                if r["type"] == "tier_classification"
            ),
            {},
        )
        routing_result = next(
            (
                r["result"]
                for r in state["rule_results"]
                if r["type"] == "routing_decision"
            ),
            {},
        )

        # Build context for LLM
        customer_message = state["messages"][-1].content
        greeting = tier_result.get("greeting", "Hello!")
        tier = tier_result.get("tier", "Standard")
        suggested_response = routing_result.get(
            "suggested_response", "general_assistance"
        )
        route_to = routing_result.get("route_to", "general_support")

        # Create prompt for LLM with rule-based context
        system_prompt = f"""You are a customer service agent. Based on the rules engine analysis:

Customer Tier: {tier}
Greeting: {greeting}
Routing: {route_to}
Suggested Response Type: {suggested_response}

Generate a helpful, professional response to the customer's message.
Keep it concise (2-3 sentences) and appropriate for their tier level."""

        # Generate response using Ollama
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": customer_message},
        ]

        llm_response = self.llm.invoke(messages)
        response = llm_response.content

        # Add tier-specific personalization
        if tier == "VIP":
            response += " As a VIP customer, you'll receive priority assistance."

        ai_message = AIMessage(content=response)

        # Append to messages instead of replacing
        new_messages = state["messages"] + [ai_message]

        return {**state, "messages": new_messages}

    def _escalate(self, state: ConversationState) -> ConversationState:
        """Handle escalation scenarios."""
        routing_result = next(
            (
                r["result"]
                for r in state["rule_results"]
                if r["type"] == "routing_decision"
            ),
            {},
        )

        escalation_level = routing_result.get("escalation_level", "standard")
        reason = routing_result.get("reason", "customer_request")

        response = (
            f"I understand this is {escalation_level}. I'm immediately "
            f"connecting you with a supervisor who can provide the "
            f"specialized assistance you need. (Escalation reason: "
            f"{reason})"
        )

        ai_message = AIMessage(content=response)

        # Append to messages instead of replacing
        new_messages = state["messages"] + [ai_message]

        return {**state, "messages": new_messages}

    def process_message(
        self, message: str, customer_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a customer message through the rule-based workflow."""
        initial_state = ConversationState(
            messages=[HumanMessage(content=message)],
            customer_data=customer_data or {},
            conversation_context={},
            rule_results=[],
            next_action="",
        )

        result = self.workflow.invoke(initial_state)

        return {
            "response": result["messages"][-1].content,
            "rule_results": result["rule_results"],
            "customer_tier": next(
                (
                    r["result"]["tier"]
                    for r in result["rule_results"]
                    if r["type"] == "tier_classification"
                ),
                "Standard",
            ),
            "routing_decision": next(
                (
                    r["result"]
                    for r in result["rule_results"]
                    if r["type"] == "routing_decision"
                ),
                {},
            ),
        }


def example_conversation_flow():
    """Demonstrate the rules-based conversation agent."""
    print("=== LangGraph + Machine Rules Agent Example ===\n")

    # Create the agent
    agent = RulesLangGraphAgent()

    # Example customer scenarios
    scenarios = [
        {
            "description": "VIP Customer with Technical Issue",
            "customer_data": {
                "customer_id": "VIP001",
                "total_spent": 25000,
                "years_customer": 5,
                "account_type": "premium",
            },
            "message": (
                "My system is completely down and I have a critical "
                "presentation in 30 minutes!"
            ),
        },
        {
            "description": "Loyal Customer with Billing Question",
            "customer_data": {
                "customer_id": "LOYAL001",
                "total_spent": 3000,
                "years_customer": 4,
                "account_type": "standard",
            },
            "message": (
                "I have a question about my latest invoice, there "
                "seems to be an extra charge."
            ),
        },
        {
            "description": "New Customer with General Inquiry",
            "customer_data": {
                "customer_id": "NEW001",
                "total_spent": 0,
                "years_customer": 0,
                "account_type": "basic",
            },
            "message": (
                "Hi, I'm new here and would like to know more about your services."
            ),
        },
        {
            "description": "Frustrated Customer",
            "customer_data": {
                "customer_id": "FRUST001",
                "total_spent": 1500,
                "years_customer": 2,
                "account_type": "standard",
            },
            "message": (
                "This is terrible! Your service is awful and I'm very frustrated!"
            ),
        },
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"Scenario {i}: {scenario['description']}")
        print(f'Customer Message: "{scenario["message"]}"')
        print(f"Customer Data: {scenario['customer_data']}")

        # Process through the agent
        result = agent.process_message(scenario["message"], scenario["customer_data"])

        print(f"\nAgent Response: {result['response']}")
        print(f"Customer Tier: {result['customer_tier']}")
        print(f"Routing Decision: {result['routing_decision']}")
        print("\n" + "=" * 60 + "\n")


def example_dynamic_rule_updates():
    """Demonstrate dynamic rule updates during conversation."""
    print("=== Dynamic Rule Updates Example ===\n")

    agent = RulesLangGraphAgent()

    # Add a new business hours rule dynamically
    business_hours_rule = Rule(
        name="after_hours_support",
        condition=lambda fact: (
            fact.get("current_hour", 12) < 9 or fact.get("current_hour", 12) > 17
        ),
        action=lambda fact: {
            "escalate": True,
            "route_to": "after_hours_team",
            "message_prefix": "Thank you for contacting us after hours.",
            "response_delay": "within_4_hours",
        },
        priority=90,
    )

    # Get existing escalation rules and add the new one
    session = agent.runtime.create_rule_session("escalation")
    existing_set = agent.admin.get_registrations()["escalation"]

    updated_rules = list(existing_set.get_rules()) + [business_hours_rule]
    updated_set = RuleExecutionSet(name="escalation_with_hours", rules=updated_rules)

    # Register updated rules
    agent.admin.register_rule_execution_set("escalation", updated_set)
    session.close()

    print("Added after-hours support rule dynamically!")

    # Test with after-hours scenario
    after_hours_scenario = {
        "customer_id": "NIGHT001",
        "total_spent": 2000,
        "years_customer": 1,
        "current_hour": 22,  # 10 PM
    }

    result = agent.process_message(
        "I need help with my account access", after_hours_scenario
    )

    print(f"After-hours response: {result['response']}")
    print(f"Routing: {result['routing_decision']}")


if __name__ == "__main__":
    print("LangGraph v1 + Machine Rules + Ollama Integration Examples")
    print("=" * 60)
    print("\nUsing Ollama model: gpt-oss:20b")
    print("Make sure Ollama is running with: ollama pull gpt-oss:20b\n")

    try:
        example_conversation_flow()
        example_dynamic_rule_updates()

        print("\n=== All LangGraph Examples Completed Successfully ===")

    except Exception as e:
        print(f"\nError running examples: {e}")
        print("\nMake sure Ollama is running and gpt-oss:20b is pulled:")
        print("  ollama serve")
        print("  ollama pull gpt-oss:20b")
        raise
