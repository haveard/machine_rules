#!/usr/bin/env python3
"""
Simple LangGraph + Machine Rules Example

A focused example showing how to use Machine Rules Engine
with LangGraph for an AI agent that routes customer inquiries
based on business rules.

This example demonstrates:
- Rule-based routing decisions in LangGraph workflows
- Combining deterministic rules with LLM reasoning
- Dynamic response generation based on rule outcomes

Requirements:
    pip install langgraph langchain-core

Note: This example works without API keys for demonstration purposes.
"""

from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, END

# Machine Rules imports
from machine_rules.api.registry import RuleServiceProviderManager
from machine_rules.api.execution_set import Rule, RuleExecutionSet


class CustomerState(TypedDict):
    """State for customer service routing workflow."""

    customer_message: str
    customer_data: Dict[str, Any]
    tier_classification: Dict[str, Any]
    routing_decision: Dict[str, Any]
    response: str


class SimpleRulesAgent:
    """A simple agent that uses rules for customer service routing."""

    def __init__(self):
        """Initialize with customer classification and routing rules."""
        self.provider = RuleServiceProviderManager.get("api")
        if not self.provider:
            raise RuntimeError("Rules engine not initialized")

        self.admin = self.provider.get_rule_administrator()
        self.runtime = self.provider.get_rule_runtime()

        self._create_customer_tier_rules()
        self._create_routing_rules()
        self._build_workflow()

    def _create_customer_tier_rules(self):
        """Create rules for customer tier classification."""
        tier_rules = [
            Rule(
                name="vip_tier",
                condition=lambda customer: customer.get("annual_spend", 0) > 10000,
                action=lambda customer: {
                    "tier": "VIP",
                    "priority": "HIGH",
                    "sla_minutes": 5,
                    "agent_level": "senior",
                },
                priority=100,
            ),
            Rule(
                name="premium_tier",
                condition=lambda customer: customer.get("annual_spend", 0) > 1000,
                action=lambda customer: {
                    "tier": "Premium",
                    "priority": "MEDIUM",
                    "sla_minutes": 15,
                    "agent_level": "standard",
                },
                priority=50,
            ),
            Rule(
                name="standard_tier",
                condition=lambda customer: True,  # Default rule
                action=lambda customer: {
                    "tier": "Standard",
                    "priority": "NORMAL",
                    "sla_minutes": 30,
                    "agent_level": "junior",
                },
                priority=1,
            ),
        ]

        tier_set = RuleExecutionSet("customer_tiers", tier_rules)
        self.admin.register_rule_execution_set("tiers", tier_set)

    def _create_routing_rules(self):
        """Create rules for routing customer inquiries."""
        routing_rules = [
            Rule(
                name="technical_emergency",
                condition=lambda inquiry: (
                    any(
                        word in inquiry.get("message", "").lower()
                        for word in ["down", "outage", "critical", "emergency"]
                    )
                    and inquiry.get("tier") == "VIP"
                ),
                action=lambda inquiry: {
                    "route_to": "technical_emergency_team",
                    "escalate": True,
                    "notify_manager": True,
                    "response_type": "emergency",
                },
                priority=100,
            ),
            Rule(
                name="billing_inquiry",
                condition=lambda inquiry: any(
                    word in inquiry.get("message", "").lower()
                    for word in ["billing", "payment", "charge", "refund", "invoice"]
                ),
                action=lambda inquiry: {
                    "route_to": "billing_team",
                    "escalate": False,
                    "response_type": "billing",
                },
                priority=75,
            ),
            Rule(
                name="technical_support",
                condition=lambda inquiry: any(
                    word in inquiry.get("message", "").lower()
                    for word in ["technical", "bug", "error", "not working", "help"]
                ),
                action=lambda inquiry: {
                    "route_to": "technical_team",
                    "escalate": False,
                    "response_type": "technical",
                },
                priority=50,
            ),
            Rule(
                name="general_inquiry",
                condition=lambda inquiry: True,
                action=lambda inquiry: {
                    "route_to": "general_support",
                    "escalate": False,
                    "response_type": "general",
                },
                priority=1,
            ),
        ]

        routing_set = RuleExecutionSet("inquiry_routing", routing_rules)
        self.admin.register_rule_execution_set("routing", routing_set)

    def _build_workflow(self):
        """Build the LangGraph workflow."""
        workflow = StateGraph(CustomerState)

        # Add workflow nodes
        workflow.add_node("classify_customer", self._classify_customer)
        workflow.add_node("route_inquiry", self._route_inquiry)
        workflow.add_node("generate_response", self._generate_response)

        # Define workflow flow
        workflow.set_entry_point("classify_customer")
        workflow.add_edge("classify_customer", "route_inquiry")
        workflow.add_edge("route_inquiry", "generate_response")
        workflow.add_edge("generate_response", END)

        self.workflow = workflow.compile()

    def _classify_customer(self, state: CustomerState) -> CustomerState:
        """Classify customer tier using rules."""
        # Apply tier classification rules
        session = self.runtime.create_rule_session("tiers")
        session.add_facts([state["customer_data"]])
        tier_results = session.execute()
        session.close()

        # Get the highest priority classification
        tier_info = (
            tier_results[0]
            if tier_results
            else {"tier": "Standard", "priority": "NORMAL"}
        )

        return {**state, "tier_classification": tier_info}

    def _route_inquiry(self, state: CustomerState) -> CustomerState:
        """Route the inquiry using rules."""
        # Combine message and tier for routing decision
        inquiry_fact = {
            "message": state["customer_message"],
            "tier": state["tier_classification"]["tier"],
            **state["customer_data"],
        }

        # Apply routing rules
        session = self.runtime.create_rule_session("routing")
        session.add_facts([inquiry_fact])
        routing_results = session.execute()
        session.close()

        # Get the highest priority routing decision
        routing_info = (
            routing_results[0]
            if routing_results
            else {"route_to": "general_support", "response_type": "general"}
        )

        return {**state, "routing_decision": routing_info}

    def _generate_response(self, state: CustomerState) -> CustomerState:
        """Generate response based on rules outcomes."""
        tier = state["tier_classification"]
        routing = state["routing_decision"]

        # Build response based on tier and routing
        if routing["response_type"] == "emergency":
            response = (
                f"URGENT: As a {tier['tier']} customer, you're being "
                f"connected immediately to our emergency technical team. "
                f"Expected response: {tier['sla_minutes']} minutes."
            )

        elif routing["response_type"] == "billing":
            response = (
                f"Thank you for contacting us about billing. As a "
                f"{tier['tier']} customer, our billing specialists will "
                f"assist you within {tier['sla_minutes']} minutes."
            )

        elif routing["response_type"] == "technical":
            response = (
                f"I understand you need technical help. You're being "
                f"routed to our {tier['agent_level']} technical support "
                f"team (SLA: {tier['sla_minutes']} minutes)."
            )

        else:
            response = (
                f"Hello! As a {tier['tier']} customer, you'll receive "
                f"{tier['priority'].lower()} priority support. How can "
                f"we help you today?"
            )

        # Add escalation notice if needed
        if routing.get("escalate"):
            response += " This inquiry has been escalated due to its urgency."

        return {**state, "response": response}

    def process_inquiry(
        self, message: str, customer_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a customer inquiry through the rule-based workflow."""
        initial_state = CustomerState(
            customer_message=message,
            customer_data=customer_data,
            tier_classification={},
            routing_decision={},
            response="",
        )

        # Run the workflow
        result = self.workflow.invoke(initial_state)

        return {
            "response": result["response"],
            "customer_tier": result["tier_classification"],
            "routing": result["routing_decision"],
        }


def run_examples():
    """Run example scenarios."""
    print("=== Simple LangGraph + Rules Engine Example ===\n")

    agent = SimpleRulesAgent()

    # Test scenarios
    scenarios = [
        {
            "name": "VIP Emergency",
            "message": "Our entire system is down! This is a critical emergency!",
            "customer": {
                "customer_id": "VIP001",
                "annual_spend": 15000,
                "account_years": 3,
            },
        },
        {
            "name": "Premium Billing Issue",
            "message": "I have a question about my latest invoice charges.",
            "customer": {
                "customer_id": "PREM001",
                "annual_spend": 5000,
                "account_years": 2,
            },
        },
        {
            "name": "Standard Technical Help",
            "message": "I'm having trouble with the login feature, it's not working.",
            "customer": {
                "customer_id": "STD001",
                "annual_spend": 500,
                "account_years": 1,
            },
        },
        {
            "name": "New Customer General Inquiry",
            "message": "Hi, I'm interested in learning more about your services.",
            "customer": {
                "customer_id": "NEW001",
                "annual_spend": 0,
                "account_years": 0,
            },
        },
    ]

    for scenario in scenarios:
        print(f"📧 Scenario: {scenario['name']}")
        print(f"💬 Message: \"{scenario['message']}\"")
        print(f"👤 Customer: {scenario['customer']}")

        # Process through agent
        result = agent.process_inquiry(scenario["message"], scenario["customer"])

        print(f"🤖 Response: {result['response']}")
        print(
            f"🏷️  Tier: {result['customer_tier']['tier']} "
            f"(Priority: {result['customer_tier']['priority']})"
        )
        print(f"🔀 Routing: {result['routing']['route_to']}")

        if result["routing"].get("escalate"):
            print("⚠️  ESCALATED")

        print("\n" + "=" * 60 + "\n")


def demonstrate_rule_modification():
    """Show how to modify rules dynamically."""
    print("=== Dynamic Rule Modification Example ===\n")

    agent = SimpleRulesAgent()

    # Test before modification
    result_before = agent.process_inquiry(
        "I need help with installation",
        {"customer_id": "TEST001", "annual_spend": 2000},
    )
    print("Before adding installation rule:")
    print(f"Response: {result_before['response']}")
    print(f"Routed to: {result_before['routing']['route_to']}\n")

    # Add a new installation-specific rule
    installation_rule = Rule(
        name="installation_support",
        condition=lambda inquiry: any(
            word in inquiry.get("message", "").lower()
            for word in ["install", "setup", "configure", "deployment"]
        ),
        action=lambda inquiry: {
            "route_to": "installation_team",
            "escalate": False,
            "response_type": "installation",
        },
        priority=80,  # Higher than general technical support
    )

    # Get existing routing rules and add new one
    existing_set = agent.admin.get_registrations()["routing"]
    updated_rules = list(existing_set.get_rules()) + [installation_rule]
    updated_set = RuleExecutionSet("updated_routing", updated_rules)

    # Re-register with new rule
    agent.admin.register_rule_execution_set("routing", updated_set)

    # Update response generation to handle installation type
    original_generate = agent._generate_response

    def enhanced_generate_response(state: CustomerState) -> CustomerState:
        if state["routing_decision"].get("response_type") == "installation":
            tier = state["tier_classification"]
            updated_state = CustomerState(
                customer_message=state["customer_message"],
                customer_data=state["customer_data"],
                tier_classification=state["tier_classification"],
                routing_decision=state["routing_decision"],
                response=(
                    f"I see you need installation help! As a "
                    f"{tier['tier']} customer, you're being connected to "
                    f"our specialized installation team who will guide "
                    f"you through the setup process."
                ),
            )
            return updated_state
        return original_generate(state)

    agent._generate_response = enhanced_generate_response

    # Rebuild workflow with updated method
    agent._build_workflow()

    # Test after modification
    result_after = agent.process_inquiry(
        "I need help with installation",
        {"customer_id": "TEST001", "annual_spend": 2000},
    )
    print("After adding installation rule:")
    print(f"Response: {result_after['response']}")
    print(f"Routed to: {result_after['routing']['route_to']}")


if __name__ == "__main__":
    try:
        run_examples()
        demonstrate_rule_modification()

        print("✅ All LangGraph + Rules examples completed successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
