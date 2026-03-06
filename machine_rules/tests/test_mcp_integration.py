"""
Integration tests for the MCP server.

These tests exercise the full MCP protocol round-trip using in-memory
streams: Client → MCP Protocol → Server → machine_rules engine → response.

This verifies that tool definitions, argument serialization, result
formatting, and error propagation all work correctly end-to-end through
the MCP transport layer.
"""

import json
from typing import Any

import anyio
import pytest
from mcp import ClientSession
from mcp.shared.message import SessionMessage
from mcp.types import TextResourceContents
from pydantic import AnyUrl

from machine_rules.mcp_server import mcp as mcp_server, _admin

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_text_content(result) -> str:
    """Extract text from a CallToolResult (text content or structured)."""
    if result.content:
        return result.content[0].text
    if result.structuredContent is not None:
        return json.dumps(
            result.structuredContent.get("result", result.structuredContent)
        )
    raise ValueError("CallToolResult has no content or structuredContent")


def _parse_json_content(result) -> Any:
    """Extract and parse JSON/structured data from a CallToolResult."""
    if result.structuredContent is not None:
        value = result.structuredContent
        # FastMCP wraps return values under a "result" key
        if isinstance(value, dict) and "result" in value:
            return value["result"]
        return value
    return json.loads(result.content[0].text)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_mcp_registrations():
    """Clear all rule sets registered with the MCP server's provider."""
    for name in list(_admin.get_registrations().keys()):
        _admin.deregister_rule_execution_set(name)
    yield
    for name in list(_admin.get_registrations().keys()):
        _admin.deregister_rule_execution_set(name)


@pytest.fixture()
def sample_rules():
    return [
        {
            "name": "high_value",
            "condition": "fact.get('value', 0) > 100",
            "action": "{'tier': 'high'}",
            "priority": 10,
        },
        {
            "name": "low_value",
            "condition": "fact.get('value', 0) <= 100",
            "action": "{'tier': 'low'}",
            "priority": 5,
        },
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMCPIntegration:
    """Full MCP protocol round-trip integration tests."""

    @staticmethod
    async def _run_with_client(fn):
        """Create in-memory MCP client↔server and run ``fn(client)``."""
        server_obj = mcp_server._mcp_server
        client_to_server_send, client_to_server_recv = (
            anyio.create_memory_object_stream[SessionMessage](10)
        )
        server_to_client_send, server_to_client_recv = (
            anyio.create_memory_object_stream[SessionMessage](10)
        )

        async with anyio.create_task_group() as tg:
            tg.start_soon(
                server_obj.run,
                client_to_server_recv,
                server_to_client_send,
                server_obj.create_initialization_options(),
            )
            async with ClientSession(
                server_to_client_recv, client_to_server_send
            ) as client:
                await client.initialize()
                await fn(client)
            tg.cancel_scope.cancel()

    # -- Tool discovery ------------------------------------------------------

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Server advertises all expected tools."""

        async def check(client: ClientSession):
            result = await client.list_tools()
            tool_names = {t.name for t in result.tools}
            expected = {
                "register_rule_set",
                "execute_rules",
                "list_rule_sets",
                "get_rule_set",
                "deregister_rule_set",
                "check_expression",
            }
            assert expected.issubset(tool_names)

        await self._run_with_client(check)

    @pytest.mark.asyncio
    async def test_tools_have_descriptions(self):
        """Every tool has a non-empty description."""

        async def check(client: ClientSession):
            result = await client.list_tools()
            for tool in result.tools:
                assert tool.description, f"Tool {tool.name} has no description"

        await self._run_with_client(check)

    # -- register_rule_set ---------------------------------------------------

    @pytest.mark.asyncio
    async def test_register_rule_set(self, sample_rules):
        """Register a rule set via MCP and verify confirmation."""

        async def check(client: ClientSession):
            result = await client.call_tool(
                "register_rule_set",
                {"name": "integration_set", "rules": sample_rules},
            )
            text = _parse_text_content(result)
            assert "integration_set" in text
            assert "2 rules" in text
            assert not result.isError

        await self._run_with_client(check)

    @pytest.mark.asyncio
    async def test_register_invalid_expression(self):
        """Registering with a dangerous expression returns an error."""

        async def check(client: ClientSession):
            bad_rules = [
                {
                    "name": "bad",
                    "condition": "__import__('os')",
                    "action": "{'x': 1}",
                }
            ]
            result = await client.call_tool(
                "register_rule_set",
                {"name": "bad_set", "rules": bad_rules},
            )
            assert result.isError

        await self._run_with_client(check)

    # -- list_rule_sets ------------------------------------------------------

    @pytest.mark.asyncio
    async def test_list_rule_sets_empty(self):
        """list_rule_sets returns empty list when nothing is registered."""

        async def check(client: ClientSession):
            result = await client.call_tool("list_rule_sets", {})
            data = _parse_json_content(result)
            assert data == []
            assert not result.isError

        await self._run_with_client(check)

    @pytest.mark.asyncio
    async def test_list_rule_sets_after_register(self, sample_rules):
        """list_rule_sets reflects a freshly registered set."""

        async def check(client: ClientSession):
            await client.call_tool(
                "register_rule_set",
                {"name": "set_a", "rules": sample_rules},
            )
            await client.call_tool(
                "register_rule_set",
                {"name": "set_b", "rules": sample_rules},
            )
            result = await client.call_tool("list_rule_sets", {})
            data = _parse_json_content(result)
            assert sorted(data) == ["set_a", "set_b"]

        await self._run_with_client(check)

    # -- execute_rules -------------------------------------------------------

    @pytest.mark.asyncio
    async def test_execute_rules_matching(self, sample_rules):
        """Execute rules and get correct results through MCP transport."""

        async def check(client: ClientSession):
            await client.call_tool(
                "register_rule_set",
                {"name": "exec_set", "rules": sample_rules},
            )
            result = await client.call_tool(
                "execute_rules",
                {
                    "rule_set_name": "exec_set",
                    "facts": [{"value": 200}, {"value": 50}],
                },
            )
            data = _parse_json_content(result)
            assert len(data) == 2
            tiers = [r["tier"] for r in data]
            assert tiers == ["high", "low"]
            assert not result.isError

        await self._run_with_client(check)

    @pytest.mark.asyncio
    async def test_execute_rules_empty_facts(self, sample_rules):
        """Executing with empty facts returns empty results."""

        async def check(client: ClientSession):
            await client.call_tool(
                "register_rule_set",
                {"name": "empty_exec", "rules": sample_rules},
            )
            result = await client.call_tool(
                "execute_rules",
                {"rule_set_name": "empty_exec", "facts": []},
            )
            data = _parse_json_content(result)
            assert data == []

        await self._run_with_client(check)

    @pytest.mark.asyncio
    async def test_execute_rules_unregistered(self):
        """Executing against an unregistered rule set returns error."""

        async def check(client: ClientSession):
            result = await client.call_tool(
                "execute_rules",
                {"rule_set_name": "nonexistent", "facts": [{"x": 1}]},
            )
            assert result.isError

        await self._run_with_client(check)

    @pytest.mark.asyncio
    async def test_execute_first_match_strategy(self):
        """FIRST_MATCH strategy returns only the highest-priority match."""

        async def check(client: ClientSession):
            rules = [
                {
                    "name": "rule_a",
                    "condition": "fact.get('x', 0) > 0",
                    "action": "{'match': 'a'}",
                    "priority": 10,
                },
                {
                    "name": "rule_b",
                    "condition": "fact.get('x', 0) > 0",
                    "action": "{'match': 'b'}",
                    "priority": 5,
                },
            ]
            await client.call_tool(
                "register_rule_set",
                {"name": "fm_set", "rules": rules, "strategy": "FIRST_MATCH"},
            )
            result = await client.call_tool(
                "execute_rules",
                {"rule_set_name": "fm_set", "facts": [{"x": 1}]},
            )
            data = _parse_json_content(result)
            assert len(data) == 1
            assert data[0]["match"] == "a"

        await self._run_with_client(check)

    # -- get_rule_set --------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_rule_set(self, sample_rules):
        """get_rule_set returns correct metadata through MCP."""

        async def check(client: ClientSession):
            await client.call_tool(
                "register_rule_set",
                {
                    "name": "info_set",
                    "rules": sample_rules,
                    "description": "Integration info test",
                },
            )
            result = await client.call_tool("get_rule_set", {"name": "info_set"})
            data = _parse_json_content(result)
            assert data["name"] == "info_set"
            assert data["description"] == "Integration info test"
            assert len(data["rules"]) == 2
            assert not result.isError

        await self._run_with_client(check)

    @pytest.mark.asyncio
    async def test_get_rule_set_nonexistent(self):
        """get_rule_set for an unknown name returns error."""

        async def check(client: ClientSession):
            result = await client.call_tool("get_rule_set", {"name": "missing"})
            assert result.isError

        await self._run_with_client(check)

    # -- deregister_rule_set -------------------------------------------------

    @pytest.mark.asyncio
    async def test_deregister_rule_set(self, sample_rules):
        """Deregistering removes the rule set from listings."""

        async def check(client: ClientSession):
            await client.call_tool(
                "register_rule_set",
                {"name": "del_set", "rules": sample_rules},
            )
            result = await client.call_tool("deregister_rule_set", {"name": "del_set"})
            text = _parse_text_content(result)
            assert "del_set" in text

            listing = await client.call_tool("list_rule_sets", {})
            data = _parse_json_content(listing)
            assert "del_set" not in data

        await self._run_with_client(check)

    # -- check_expression ----------------------------------------------------

    @pytest.mark.asyncio
    async def test_check_expression_safe(self):
        """check_expression for a simple arithmetic expression."""

        async def check(client: ClientSession):
            result = await client.call_tool(
                "check_expression", {"expression": "1 + 2 * 3"}
            )
            data = _parse_json_content(result)
            assert data["safe"] is True
            assert data["expression"] == "1 + 2 * 3"
            assert not result.isError

        await self._run_with_client(check)

    @pytest.mark.asyncio
    async def test_check_expression_unsafe(self):
        """check_expression rejects dangerous patterns."""

        async def check(client: ClientSession):
            result = await client.call_tool(
                "check_expression", {"expression": "__import__('os')"}
            )
            data = _parse_json_content(result)
            assert data["safe"] is False

        await self._run_with_client(check)

    # -- Resource access -----------------------------------------------------

    @pytest.mark.asyncio
    async def test_read_resource(self, sample_rules):
        """Reading a rules://{name} resource returns rule set JSON."""

        async def check(client: ClientSession):
            await client.call_tool(
                "register_rule_set",
                {
                    "name": "res_set",
                    "rules": sample_rules,
                    "description": "Resource integration test",
                },
            )
            result = await client.read_resource(AnyUrl("rules://res_set"))
            content = result.contents[0]
            assert isinstance(content, TextResourceContents)
            data = json.loads(content.text)
            assert data["name"] == "res_set"
            assert data["description"] == "Resource integration test"
            assert len(data["rules"]) == 2

        await self._run_with_client(check)

    @pytest.mark.asyncio
    async def test_list_resource_templates(self):
        """Server advertises the rules:// resource template."""

        async def check(client: ClientSession):
            result = await client.list_resource_templates()
            uris = [t.uriTemplate for t in result.resourceTemplates]
            assert any("rules://" in u for u in uris)

        await self._run_with_client(check)

    # -- End-to-end workflow -------------------------------------------------

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Complete workflow: register → execute → inspect → deregister."""

        async def check(client: ClientSession):
            rules = [
                {
                    "name": "premium",
                    "condition": "fact.get('score', 0) >= 80",
                    "action": "{'tier': 'premium', 'discount': 0.2}",
                    "priority": 10,
                },
                {
                    "name": "standard",
                    "condition": "fact.get('score', 0) >= 50",
                    "action": "{'tier': 'standard', 'discount': 0.1}",
                    "priority": 5,
                },
                {
                    "name": "basic",
                    "condition": "fact.get('score', 0) < 50",
                    "action": "{'tier': 'basic', 'discount': 0.0}",
                    "priority": 1,
                },
            ]

            # 1. Register
            reg_result = await client.call_tool(
                "register_rule_set",
                {
                    "name": "loyalty",
                    "rules": rules,
                    "description": "Customer loyalty tiers",
                    "strategy": "FIRST_MATCH",
                },
            )
            assert not reg_result.isError

            # 2. Verify listing
            listing = await client.call_tool("list_rule_sets", {})
            assert "loyalty" in _parse_json_content(listing)

            # 3. Inspect
            info = await client.call_tool("get_rule_set", {"name": "loyalty"})
            info_data = _parse_json_content(info)
            assert info_data["name"] == "loyalty"
            assert len(info_data["rules"]) == 3

            # 4. Execute with multiple facts
            exec_result = await client.call_tool(
                "execute_rules",
                {
                    "rule_set_name": "loyalty",
                    "facts": [
                        {"score": 90},
                        {"score": 60},
                        {"score": 30},
                    ],
                },
            )
            results = _parse_json_content(exec_result)
            assert len(results) == 3
            assert results[0]["tier"] == "premium"
            assert results[1]["tier"] == "standard"
            assert results[2]["tier"] == "basic"

            # 5. Read via resource
            resource = await client.read_resource(AnyUrl("rules://loyalty"))
            loyalty_content = resource.contents[0]
            assert isinstance(loyalty_content, TextResourceContents)
            res_data = json.loads(loyalty_content.text)
            assert res_data["description"] == "Customer loyalty tiers"

            # 6. Deregister
            del_result = await client.call_tool(
                "deregister_rule_set", {"name": "loyalty"}
            )
            assert not del_result.isError

            # 7. Verify gone
            final_listing = await client.call_tool("list_rule_sets", {})
            assert "loyalty" not in _parse_json_content(final_listing)

        await self._run_with_client(check)
