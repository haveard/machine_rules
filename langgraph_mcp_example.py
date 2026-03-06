#!/usr/bin/env python3
"""
LangGraph + Machine Rules MCP Client Example

This example demonstrates how to build a LangGraph agent that connects to the
Machine Rules MCP server and executes business rules via the Model Context
Protocol (MCP).

Two usage patterns are shown:

1. **Direct MCP client** — call tools programmatically without an LLM:
   register rule sets, execute rules, validate expressions, etc.

2. **LangGraph agent** — a state machine whose nodes delegate rule
   classification and routing to the MCP server, with an Ollama LLM
   generating the final natural-language response.

The MCP transport used here is an in-memory pipe (no separate process
needed), which is ideal for testing and single-process deployments.  To
connect to an external MCP server over stdio instead, replace the
``mcp_rules_client`` context manager with:

    from mcp import StdioServerParameters
    from mcp.client.stdio import stdio_client

    server_params = StdioServerParameters(
        command="python",
        args=["-m", "machine_rules.mcp_server"],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            ...

Requirements:
    pip install "machine-rules[mcp]" langgraph langchain-ollama langchain-core

    # Ensure Ollama is running with the model:
    ollama pull gpt-oss:20b
"""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, Dict, List, TypedDict

import anyio
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from mcp import ClientSession
from mcp.shared.message import SessionMessage

# Import the FastMCP server instance — used for the in-memory transport only.
# For external/stdio transport this import is not required.
from machine_rules.mcp_server import mcp as _mcp_server_instance


# ---------------------------------------------------------------------------
# Helpers: extract content from CallToolResult
# ---------------------------------------------------------------------------


def _extract_text(result) -> str:
    """Return a string from a CallToolResult (text or structured content)."""
    if result.content:
        return result.content[0].text
    if result.structuredContent is not None:
        val = result.structuredContent
        return json.dumps(val.get("result", val))
    return ""


def _extract_structured(result):
    """Return the Python object from a CallToolResult."""
    if result.structuredContent is not None:
        val = result.structuredContent
        if isinstance(val, dict) and "result" in val:
            return val["result"]
        return val
    if result.content:
        return json.loads(result.content[0].text)
    return None


# ---------------------------------------------------------------------------
# Thin async wrapper around a connected MCP ClientSession
# ---------------------------------------------------------------------------


class MCPRulesClient:
    """Typed async wrapper over ``mcp.ClientSession`` for the Machine Rules MCP server."""

    def __init__(self, session: ClientSession):
        self._session = session

    async def register_rule_set(
        self,
        name: str,
        rules: List[Dict[str, Any]],
        description: str = "",
        strategy: str = "ALL_MATCHES",
    ) -> str:
        result = await self._session.call_tool(
            "register_rule_set",
            {
                "name": name,
                "rules": rules,
                "description": description,
                "strategy": strategy,
            },
        )
        return _extract_text(result)

    async def execute_rules(
        self, rule_set_name: str, facts: List[Dict[str, Any]]
    ) -> List[Any]:
        result = await self._session.call_tool(
            "execute_rules",
            {"rule_set_name": rule_set_name, "facts": facts},
        )
        return _extract_structured(result) or []

    async def list_rule_sets(self) -> List[str]:
        result = await self._session.call_tool("list_rule_sets", {})
        return _extract_structured(result) or []

    async def get_rule_set(self, name: str) -> Dict[str, Any]:
        result = await self._session.call_tool("get_rule_set", {"name": name})
        return _extract_structured(result) or {}

    async def deregister_rule_set(self, name: str) -> str:
        result = await self._session.call_tool("deregister_rule_set", {"name": name})
        return _extract_text(result)

    async def check_expression(self, expression: str) -> Dict[str, Any]:
        result = await self._session.call_tool(
            "check_expression", {"expression": expression}
        )
        return _extract_structured(result) or {}


# ---------------------------------------------------------------------------
# Context manager: in-memory MCP transport
# ---------------------------------------------------------------------------


@asynccontextmanager
async def mcp_rules_client():
    """
    Async context manager that yields a connected :class:`MCPRulesClient`.

    Uses an in-memory anyio stream pair so no separate server process is
    needed.  The MCP handshake (``initialize``) is performed automatically.
    """
    server = _mcp_server_instance._mcp_server
    c2s_send, c2s_recv = anyio.create_memory_object_stream[SessionMessage](32)
    s2c_send, s2c_recv = anyio.create_memory_object_stream[SessionMessage](32)

    async with anyio.create_task_group() as tg:
        tg.start_soon(
            server.run,
            c2s_recv,
            s2c_send,
            server.create_initialization_options(),
        )
        async with ClientSession(s2c_recv, c2s_send) as session:
            await session.initialize()
            yield MCPRulesClient(session)
        tg.cancel_scope.cancel()


# ---------------------------------------------------------------------------
# LangGraph agent
# ---------------------------------------------------------------------------


class AgentState(TypedDict):
    customer: Dict[str, Any]
    message: str
    tier: Dict[str, Any]
    routing: Dict[str, Any]
    response: str
    messages: List[BaseMessage]


class LangGraphMCPAgent:
    """
    LangGraph agent that delegates all rule logic to the Machine Rules MCP server.

    Graph topology::

        START → classify_customer → route_inquiry → generate_response → END

    * ``classify_customer``  — calls ``execute_rules("customer_tiers", ...)`` via MCP
    * ``route_inquiry``      — calls ``execute_rules("routing", ...)`` via MCP
    * ``generate_response``  — uses Ollama to compose a natural-language reply
    """

    TIER_RULES = [
        {
            "name": "vip",
            "condition": (
                "fact.get('total_spent', 0) > 10000 "
                "or fact.get('account_type') == 'premium'"
            ),
            "action": (
                "{'tier': 'VIP', 'priority': 'high', 'sla_minutes': 5, "
                "'greeting': 'Thank you for being a valued VIP customer!'}"
            ),
            "priority": 100,
        },
        {
            "name": "loyal",
            "condition": (
                "fact.get('years_customer', 0) > 2 or fact.get('total_spent', 0) > 1000"
            ),
            "action": (
                "{'tier': 'Loyal', 'priority': 'medium', 'sla_minutes': 15, "
                "'greeting': 'Thank you for your continued loyalty!'}"
            ),
            "priority": 50,
        },
        {
            "name": "standard",
            "condition": "True",
            "action": (
                "{'tier': 'Standard', 'priority': 'standard', 'sla_minutes': 30, "
                "'greeting': 'Welcome! How can we help you today?'}"
            ),
            "priority": 1,
        },
    ]

    ROUTING_RULES = [
        {
            "name": "urgent",
            "condition": (
                "any(kw in fact.get('message', '').lower() "
                "for kw in ['urgent', 'emergency', 'critical', 'down', 'broken'])"
            ),
            "action": (
                "{'route': 'supervisor', 'escalate': True, "
                "'response_type': 'emergency'}"
            ),
            "priority": 100,
        },
        {
            "name": "technical",
            "condition": (
                "any(kw in fact.get('message', '').lower() "
                "for kw in ['bug', 'error', 'crash', 'not working', 'technical'])"
            ),
            "action": (
                "{'route': 'technical_support', 'escalate': False, "
                "'response_type': 'tech_help'}"
            ),
            "priority": 75,
        },
        {
            "name": "billing",
            "condition": (
                "any(kw in fact.get('message', '').lower() "
                "for kw in ['billing', 'charge', 'refund', 'invoice', 'payment'])"
            ),
            "action": (
                "{'route': 'billing', 'escalate': False, "
                "'response_type': 'billing_help'}"
            ),
            "priority": 75,
        },
        {
            "name": "general",
            "condition": "True",
            "action": (
                "{'route': 'general_support', 'escalate': False, "
                "'response_type': 'general_help'}"
            ),
            "priority": 1,
        },
    ]

    def __init__(self, client: MCPRulesClient):
        self._client = client
        self._llm = ChatOllama(model="gpt-oss:20b", temperature=0.7)

    async def setup(self) -> None:
        """Register rule sets via MCP once per agent lifecycle."""
        existing = await self._client.list_rule_sets()
        if "customer_tiers" not in existing:
            msg = await self._client.register_rule_set(
                name="customer_tiers",
                rules=self.TIER_RULES,
                description="Customer tier classification",
                strategy="FIRST_MATCH",
            )
            print(f"  MCP ← {msg}")
        if "routing" not in existing:
            msg = await self._client.register_rule_set(
                name="routing",
                rules=self.ROUTING_RULES,
                description="Inquiry routing and escalation",
                strategy="FIRST_MATCH",
            )
            print(f"  MCP ← {msg}")

    def build_graph(self) -> Any:
        """Construct and compile the LangGraph state machine."""
        graph = StateGraph(AgentState)
        graph.add_node("classify_customer", self._classify_customer)
        graph.add_node("route_inquiry", self._route_inquiry)
        graph.add_node("generate_response", self._generate_response)
        graph.add_edge(START, "classify_customer")
        graph.add_edge("classify_customer", "route_inquiry")
        graph.add_edge("route_inquiry", "generate_response")
        graph.add_edge("generate_response", END)
        return graph.compile()

    # -- Graph nodes ---------------------------------------------------------

    async def _classify_customer(self, state: AgentState) -> AgentState:
        """Classify the customer tier by calling execute_rules via MCP."""
        results = await self._client.execute_rules(
            "customer_tiers", [state["customer"]]
        )
        tier = results[0] if results else {"tier": "Standard", "sla_minutes": 30}
        return {**state, "tier": tier}

    async def _route_inquiry(self, state: AgentState) -> AgentState:
        """Determine routing by calling execute_rules via MCP."""
        fact = {**state["customer"], "message": state["message"]}
        results = await self._client.execute_rules("routing", [fact])
        routing = (
            results[0]
            if results
            else {
                "route": "general_support",
                "escalate": False,
                "response_type": "general_help",
            }
        )
        return {**state, "routing": routing}

    async def _generate_response(self, state: AgentState) -> AgentState:
        """Generate a natural-language reply with Ollama, guided by rule outputs."""
        tier = state["tier"]
        routing = state["routing"]

        if routing.get("escalate"):
            text = (
                f"{tier.get('greeting', '')} I'm escalating your urgent matter "
                "immediately to a senior representative."
            )
        else:
            system_prompt = (
                f"You are a customer service agent. "
                f"Customer tier: {tier.get('tier', 'Standard')} — "
                f"{tier.get('greeting', '')} "
                f"Response type: {routing.get('response_type', 'general_help')}. "
                f"Reply helpfully in 2–3 sentences."
            )
            ai_resp = await self._llm.ainvoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": state["message"]},
                ]
            )
            text = ai_resp.content

        new_messages = state.get("messages", []) + [AIMessage(content=text)]
        return {**state, "response": text, "messages": new_messages}

    # -- Public API ----------------------------------------------------------

    async def process(self, message: str, customer: Dict[str, Any]) -> Dict[str, Any]:
        """Run the LangGraph workflow for a single customer inquiry."""
        graph = self.build_graph()
        result = await graph.ainvoke(
            AgentState(
                customer=customer,
                message=message,
                tier={},
                routing={},
                response="",
                messages=[HumanMessage(content=message)],
            )
        )
        return {
            "response": result["response"],
            "tier": result["tier"],
            "routing": result["routing"],
        }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


async def _demo_direct_mcp(client: MCPRulesClient) -> None:
    """Demonstrate calling MCP tools directly — no LLM involved."""
    print("─" * 60)
    print("Pattern 1: Direct MCP tool usage")
    print("─" * 60)

    # List available tools from the server
    tools_result = await client._session.list_tools()
    print(f"\nAvailable MCP tools ({len(tools_result.tools)}):")
    for t in tools_result.tools:
        print(f"  • {t.name}")

    # Register a loan-approval rule set
    print()
    msg = await client.register_rule_set(
        name="loan_approval",
        description="Loan approval decision rules",
        strategy="FIRST_MATCH",
        rules=[
            {
                "name": "excellent_credit",
                "condition": (
                    "fact.get('credit_score', 0) >= 750 "
                    "and fact.get('income', 0) >= 50000"
                ),
                "action": "{'approved': True, 'rate': 3.5, 'max_amount': 500000}",
                "priority": 100,
            },
            {
                "name": "good_credit",
                "condition": "fact.get('credit_score', 0) >= 650",
                "action": "{'approved': True, 'rate': 6.5, 'max_amount': 200000}",
                "priority": 50,
            },
            {
                "name": "denied",
                "condition": "True",
                "action": "{'approved': False, 'reason': 'credit_score_below_minimum'}",
                "priority": 1,
            },
        ],
    )
    print(f"MCP ← {msg}")

    # Execute rules against applicants
    applicants = [
        {"name": "Alice", "credit_score": 780, "income": 120_000},
        {"name": "Bob", "credit_score": 670, "income": 45_000},
        {"name": "Carol", "credit_score": 580, "income": 38_000},
    ]
    results = await client.execute_rules("loan_approval", applicants)

    print("\nLoan decisions:")
    for applicant, decision in zip(applicants, results):
        if decision.get("approved"):
            status = "✅ APPROVED"
            details = f"rate={decision['rate']}%  max=${decision['max_amount']:,}"
        else:
            status = "❌ DENIED  "
            details = f"reason={decision['reason']}"
        print(f"  {status}  {applicant['name']:<8}  {details}")

    # Validate expression safety
    print("\nExpression safety checks:")
    expressions = [
        "fact.get('score', 0) >= 80",
        "__import__('os').system('rm -rf /')",
        "eval('1 + 1')",
    ]
    for expr in expressions:
        check = await client.check_expression(expr)
        icon = "✅" if check["safe"] else "🚫"
        print(f"  {icon}  {expr}")

    # List registered rule sets
    rule_sets = await client.list_rule_sets()
    print(f"\nCurrently registered rule sets: {rule_sets}")


async def _demo_langgraph_agent(client: MCPRulesClient) -> None:
    """Demonstrate a LangGraph agent using MCP-backed rules."""
    print()
    print("─" * 60)
    print("Pattern 2: LangGraph agent with MCP-powered rule execution")
    print("─" * 60)
    print()

    agent = LangGraphMCPAgent(client)
    await agent.setup()

    scenarios = [
        {
            "customer": {
                "total_spent": 15_000,
                "years_customer": 5,
                "account_type": "premium",
            },
            "message": "My system is completely down! This is an emergency!",
        },
        {
            "customer": {"total_spent": 2_000, "years_customer": 3},
            "message": "I have a question about my last invoice and the charge on it.",
        },
        {
            "customer": {"total_spent": 300, "years_customer": 1},
            "message": "How do I reset my password?",
        },
    ]

    for i, scenario in enumerate(scenarios, 1):
        result = await agent.process(scenario["message"], scenario["customer"])
        tier = result["tier"].get("tier", "?")
        route = result["routing"].get("route", "?")
        escalated = "⚠️  ESCALATED" if result["routing"].get("escalate") else ""
        sla = result["tier"].get("sla_minutes", "?")

        print(f"Scenario {i} — [{tier} tier | SLA {sla}min | → {route}] {escalated}")
        print(f"  Customer : {scenario['message']}")
        print(f"  Response : {result['response'][:120].rstrip()}...")
        print()


async def main():
    print("=" * 60)
    print("  LangGraph + Machine Rules MCP Client Example")
    print("=" * 60)
    print()

    async with mcp_rules_client() as client:
        await _demo_direct_mcp(client)
        await _demo_langgraph_agent(client)

        # Clean up all rule sets registered during the demo
        for name in await client.list_rule_sets():
            await client.deregister_rule_set(name)

    print("✅  Example complete.")


if __name__ == "__main__":
    asyncio.run(main())
