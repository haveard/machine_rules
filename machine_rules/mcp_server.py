"""
MCP Server for Machine Rules Engine.

Exposes the JSR-94 compatible rule engine as MCP tools and resources
for consumption by LLM agents and MCP-compatible clients.

Usage:
    python -m machine_rules.mcp_server
    mcp run machine_rules/mcp_server.py
"""

import json
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from machine_rules.adapters.machine_adapter import MachineRuleServiceProvider
from machine_rules.api.exceptions import RuleEngineError
from machine_rules.loader.yaml_loader import YAMLRuleLoader
from machine_rules.security.safe_evaluator import validate_expression

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "machine-rules",
    instructions="JSR-94 compatible rule engine for Python — register, inspect, and execute business rules",
)

# Bootstrap a dedicated provider for the MCP server
_provider = MachineRuleServiceProvider()
_admin = _provider.get_rule_administrator()
_runtime = _provider.get_rule_runtime()


@mcp.tool()
def register_rule_set(
    name: str,
    rules: list[dict[str, Any]],
    description: str = "",
    strategy: str = "ALL_MATCHES",
) -> str:
    """Register a new rule execution set.

    Args:
        name: Unique identifier for the rule set.
        rules: List of rule definitions, each with keys: name, condition, action, priority (optional).
        description: Human-readable description of the rule set.
        strategy: Execution strategy — "ALL_MATCHES" (default) or "FIRST_MATCH".

    Returns:
        Confirmation message with rule set name and rule count.
    """
    data: dict[str, Any] = {
        "name": name,
        "description": description,
        "rules": rules,
    }
    execution_set = YAMLRuleLoader.from_dict(data)
    if strategy in ("ALL_MATCHES", "FIRST_MATCH"):
        execution_set.properties["strategy"] = strategy
    _admin.register_rule_execution_set(name, execution_set)
    return f"Registered rule set '{name}' with {len(rules)} rules"


@mcp.tool()
def execute_rules(rule_set_name: str, facts: list[dict[str, Any]]) -> list[Any]:
    """Execute a registered rule set against a list of facts.

    Args:
        rule_set_name: URI of a registered rule execution set.
        facts: List of fact dictionaries to evaluate against the rules.

    Returns:
        List of results produced by matched rule actions.
    """
    session = _runtime.create_rule_session(rule_set_name, stateless=True)
    try:
        session.add_facts(facts)
        return session.execute()
    finally:
        session.close()


@mcp.tool()
def list_rule_sets() -> list[str]:
    """List all registered rule execution set URIs."""
    return _runtime.get_registrations()


@mcp.tool()
def get_rule_set(name: str, include_expressions: bool = False) -> dict[str, Any]:
    """Retrieve the definition of a registered rule set.

    Args:
        name: URI of the rule set to inspect.
        include_expressions: If True, include condition/action expressions in the response.

    Returns:
        Rule set metadata including name, description, properties, and rules.
    """
    registrations = _admin.get_registrations()
    if name not in registrations:
        raise RuleEngineError(f"No rule set registered with name: {name}")
    execution_set = registrations[name]
    rules_info = []
    for r in execution_set.get_rules():
        entry: dict[str, Any] = {"name": r.name, "priority": r.priority}
        if include_expressions:
            entry["condition"] = getattr(r, "_condition_expr", None)
            entry["action"] = getattr(r, "_action_expr", None)
        rules_info.append(entry)
    return {
        "name": execution_set.get_name(),
        "description": execution_set.get_description(),
        "properties": execution_set.get_properties(),
        "rules": rules_info,
    }


@mcp.tool()
def deregister_rule_set(name: str) -> str:
    """Remove a registered rule execution set.

    Args:
        name: URI of the rule set to remove.

    Returns:
        Confirmation message.
    """
    _admin.deregister_rule_execution_set(name)
    return f"Deregistered rule set '{name}'"


@mcp.tool()
def check_expression(expression: str) -> dict[str, Any]:
    """Check whether a rule expression is safe for use in conditions or actions.

    Args:
        expression: The expression string to validate.

    Returns:
        Dict with 'safe' (bool) and 'expression' (str) keys.
    """
    safe = validate_expression(expression)
    return {"safe": safe, "expression": expression}


@mcp.resource("rules://{name}")
def get_rule_set_resource(name: str) -> str:
    """Read-only resource exposing a registered rule set as JSON."""
    result = get_rule_set(name)
    return json.dumps(result, indent=2, default=str)


if __name__ == "__main__":
    mcp.run()
