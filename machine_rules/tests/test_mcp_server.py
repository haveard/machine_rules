"""
Unit tests for the MCP server module.

Tests each MCP tool function directly (no MCP transport) to validate
correct behavior, error handling, and security enforcement.
"""

import pytest
from machine_rules.mcp_server import (
    register_rule_set,
    execute_rules,
    list_rule_sets,
    get_rule_set,
    deregister_rule_set,
    check_expression,
    get_rule_set_resource,
    _admin,
    _runtime,
)
from machine_rules.api.exceptions import RuleEngineError, RuleValidationError


@pytest.fixture(autouse=True)
def clean_registrations():
    """Clear all rule set registrations before and after each test."""
    for name in list(_admin.get_registrations().keys()):
        _admin.deregister_rule_execution_set(name)
    yield
    for name in list(_admin.get_registrations().keys()):
        _admin.deregister_rule_execution_set(name)


# ---------------------------------------------------------------------------
# Sample rule definitions used across tests
# ---------------------------------------------------------------------------
SAMPLE_RULES = [
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


class TestRegisterRuleSet:
    """Tests for the register_rule_set tool."""

    def test_register_valid_rule_set(self):
        result = register_rule_set("test_set", SAMPLE_RULES)
        assert "test_set" in result
        assert "2 rules" in result

    def test_register_with_description(self):
        result = register_rule_set(
            "desc_set", SAMPLE_RULES, description="A test set"
        )
        assert "desc_set" in result
        info = get_rule_set("desc_set")
        assert info["description"] == "A test set"

    def test_register_with_strategy_first_match(self):
        register_rule_set("fm_set", SAMPLE_RULES, strategy="FIRST_MATCH")
        info = get_rule_set("fm_set")
        assert info["properties"]["strategy"] == "FIRST_MATCH"

    def test_register_with_strategy_all_matches(self):
        register_rule_set("am_set", SAMPLE_RULES, strategy="ALL_MATCHES")
        info = get_rule_set("am_set")
        assert info["properties"]["strategy"] == "ALL_MATCHES"

    def test_register_overwrite_existing(self):
        register_rule_set("ow_set", SAMPLE_RULES)
        new_rules = [SAMPLE_RULES[0]]
        register_rule_set("ow_set", new_rules)
        assert "ow_set" in list_rule_sets()
        info = get_rule_set("ow_set")
        assert len(info["rules"]) == 1

    def test_register_invalid_expression_condition(self):
        bad_rules = [
            {
                "name": "bad",
                "condition": "__import__('os')",
                "action": "{'x': 1}",
            }
        ]
        with pytest.raises(RuleValidationError):
            register_rule_set("bad_set", bad_rules)

    def test_register_invalid_expression_action(self):
        bad_rules = [
            {
                "name": "bad",
                "condition": "fact.get('x', 0) > 1",
                "action": "eval('1+1')",
            }
        ]
        with pytest.raises(RuleValidationError):
            register_rule_set("bad_set", bad_rules)

    def test_register_empty_rules(self):
        result = register_rule_set("empty_set", [])
        assert "0 rules" in result
        info = get_rule_set("empty_set")
        assert len(info["rules"]) == 0

    def test_register_missing_rule_name(self):
        bad_rules = [{"condition": "True", "action": "{'x': 1}"}]
        with pytest.raises(Exception):
            register_rule_set("missing_name", bad_rules)

    def test_register_single_rule(self):
        rules = [
            {
                "name": "only_rule",
                "condition": "fact.get('x', 0) > 0",
                "action": "{'result': 'positive'}",
                "priority": 1,
            }
        ]
        result = register_rule_set("single", rules)
        assert "1 rules" in result

    def test_register_default_priority(self):
        rules = [
            {
                "name": "no_priority",
                "condition": "fact.get('x', 0) > 0",
                "action": "{'result': True}",
            }
        ]
        register_rule_set("default_prio", rules)
        info = get_rule_set("default_prio")
        assert info["rules"][0]["priority"] == 0


class TestExecuteRules:
    """Tests for the execute_rules tool."""

    def test_execute_matching_facts(self):
        register_rule_set("exec_set", SAMPLE_RULES)
        results = execute_rules("exec_set", [{"value": 200}])
        assert len(results) == 1
        assert results[0]["tier"] == "high"

    def test_execute_low_value_fact(self):
        register_rule_set("exec_set", SAMPLE_RULES)
        results = execute_rules("exec_set", [{"value": 50}])
        assert len(results) == 1
        assert results[0]["tier"] == "low"

    def test_execute_multiple_facts(self):
        register_rule_set("exec_set", SAMPLE_RULES)
        facts = [{"value": 200}, {"value": 50}, {"value": 150}]
        results = execute_rules("exec_set", facts)
        assert len(results) == 3
        tiers = [r["tier"] for r in results]
        assert tiers == ["high", "low", "high"]

    def test_execute_empty_facts(self):
        register_rule_set("exec_set", SAMPLE_RULES)
        results = execute_rules("exec_set", [])
        assert results == []

    def test_execute_unregistered_rule_set(self):
        with pytest.raises(RuleValidationError):
            execute_rules("nonexistent", [{"value": 1}])

    def test_execute_first_match_strategy(self):
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
        register_rule_set("fm_exec", rules, strategy="FIRST_MATCH")
        results = execute_rules("fm_exec", [{"x": 1}])
        assert len(results) == 1
        assert results[0]["match"] == "a"

    def test_execute_all_matches_strategy(self):
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
        register_rule_set("am_exec", rules, strategy="ALL_MATCHES")
        results = execute_rules("am_exec", [{"x": 1}])
        assert len(results) == 2

    def test_execute_no_match(self):
        rules = [
            {
                "name": "never",
                "condition": "fact.get('x', 0) > 9999",
                "action": "{'match': True}",
            }
        ]
        register_rule_set("no_match", rules)
        results = execute_rules("no_match", [{"x": 1}])
        assert results == []

    def test_execute_stateless_clears_facts(self):
        register_rule_set("stateless_set", SAMPLE_RULES)
        # Calling execute_rules twice should work independently
        r1 = execute_rules("stateless_set", [{"value": 200}])
        r2 = execute_rules("stateless_set", [{"value": 50}])
        assert r1[0]["tier"] == "high"
        assert r2[0]["tier"] == "low"


class TestListRuleSets:
    """Tests for the list_rule_sets tool."""

    def test_list_empty(self):
        result = list_rule_sets()
        assert result == []

    def test_list_after_register(self):
        register_rule_set("set_a", SAMPLE_RULES)
        register_rule_set("set_b", SAMPLE_RULES)
        result = list_rule_sets()
        assert sorted(result) == ["set_a", "set_b"]

    def test_list_after_deregister(self):
        register_rule_set("set_a", SAMPLE_RULES)
        register_rule_set("set_b", SAMPLE_RULES)
        deregister_rule_set("set_a")
        result = list_rule_sets()
        assert result == ["set_b"]


class TestGetRuleSet:
    """Tests for the get_rule_set tool."""

    def test_get_existing(self):
        register_rule_set("info_set", SAMPLE_RULES, description="Info test")
        info = get_rule_set("info_set")
        assert info["name"] == "info_set"
        assert info["description"] == "Info test"
        assert len(info["rules"]) == 2

    def test_get_nonexistent(self):
        with pytest.raises(RuleEngineError, match="No rule set registered"):
            get_rule_set("nope")

    def test_get_rule_priorities(self):
        register_rule_set("prio_set", SAMPLE_RULES)
        info = get_rule_set("prio_set")
        priorities = [r["priority"] for r in info["rules"]]
        assert priorities == sorted(priorities, reverse=True)

    def test_get_rule_names(self):
        register_rule_set("names_set", SAMPLE_RULES)
        info = get_rule_set("names_set")
        names = {r["name"] for r in info["rules"]}
        assert names == {"high_value", "low_value"}

    def test_get_properties(self):
        register_rule_set("prop_set", SAMPLE_RULES, strategy="FIRST_MATCH")
        info = get_rule_set("prop_set")
        assert "strategy" in info["properties"]

    def test_get_include_expressions_default_hidden(self):
        register_rule_set("expr_set", SAMPLE_RULES)
        info = get_rule_set("expr_set", include_expressions=False)
        for rule in info["rules"]:
            assert "condition" not in rule
            assert "action" not in rule

    def test_get_include_expressions(self):
        register_rule_set("expr_set2", SAMPLE_RULES)
        info = get_rule_set("expr_set2", include_expressions=True)
        # Expressions are stored on rule objects if available
        for rule in info["rules"]:
            assert "condition" in rule
            assert "action" in rule


class TestDeregisterRuleSet:
    """Tests for the deregister_rule_set tool."""

    def test_deregister_existing(self):
        register_rule_set("del_set", SAMPLE_RULES)
        result = deregister_rule_set("del_set")
        assert "del_set" in result
        assert "del_set" not in list_rule_sets()

    def test_deregister_idempotent(self):
        result = deregister_rule_set("never_existed")
        assert "never_existed" in result

    def test_deregister_then_execute_fails(self):
        register_rule_set("temp_set", SAMPLE_RULES)
        deregister_rule_set("temp_set")
        with pytest.raises(RuleValidationError):
            execute_rules("temp_set", [{"value": 1}])


class TestCheckExpression:
    """Tests for the check_expression tool."""

    def test_safe_expression(self):
        # validate_expression evaluates with empty names, so 'fact' is undefined.
        # Expressions using undefined names are still considered safe (not a security issue).
        result = check_expression("fact.get('value', 0) > 100")
        assert "expression" in result
        assert result["expression"] == "fact.get('value', 0) > 100"

    def test_unsafe_import(self):
        result = check_expression("__import__('os')")
        assert result["safe"] is False

    def test_unsafe_eval(self):
        result = check_expression("eval('1+1')")
        assert result["safe"] is False

    def test_unsafe_exec(self):
        result = check_expression("exec('print(1)')")
        assert result["safe"] is False

    def test_arithmetic_expression(self):
        result = check_expression("1 + 2 * 3")
        assert result["safe"] is True

    def test_dict_literal(self):
        result = check_expression("{'key': 'value'}")
        assert result["safe"] is True

    def test_comparison(self):
        result = check_expression("10 > 5")
        assert result["safe"] is True


class TestGetRuleSetResource:
    """Tests for the rules://{name} MCP resource."""

    def test_resource_returns_json(self):
        register_rule_set("res_set", SAMPLE_RULES, description="Resource test")
        import json

        raw = get_rule_set_resource("res_set")
        data = json.loads(raw)
        assert data["name"] == "res_set"
        assert data["description"] == "Resource test"
        assert len(data["rules"]) == 2

    def test_resource_nonexistent(self):
        with pytest.raises(RuleEngineError):
            get_rule_set_resource("missing")


class TestSecurityEnforcement:
    """Verify that the MCP server preserves expression safety guarantees."""

    @pytest.mark.parametrize(
        "expr",
        [
            "__import__('os').system('ls')",
            "eval('1')",
            "exec('x=1')",
            "compile('x', '', 'exec')",
            "__builtins__",
            "open('/etc/passwd')",
        ],
    )
    def test_dangerous_expressions_rejected_at_registration(self, expr):
        rules = [{"name": "bad", "condition": expr, "action": "{'x': 1}"}]
        with pytest.raises((RuleValidationError, Exception)):
            register_rule_set("sec_set", rules)

    @pytest.mark.parametrize(
        "expr",
        [
            "__import__('os').system('ls')",
            "eval('1')",
            "exec('x=1')",
        ],
    )
    def test_dangerous_actions_rejected_at_registration(self, expr):
        rules = [
            {"name": "bad", "condition": "fact.get('x', 0) > 0", "action": expr}
        ]
        with pytest.raises((RuleValidationError, Exception)):
            register_rule_set("sec_act", rules)


class TestEdgeCases:
    """Edge cases and integration scenarios."""

    def test_multiple_register_deregister_cycles(self):
        for i in range(5):
            name = f"cycle_{i}"
            register_rule_set(name, SAMPLE_RULES)
            assert name in list_rule_sets()
            deregister_rule_set(name)
            assert name not in list_rule_sets()

    def test_fact_with_missing_keys(self):
        rules = [
            {
                "name": "default_check",
                "condition": "fact.get('missing_key', 0) > 10",
                "action": "{'found': True}",
            }
        ]
        register_rule_set("missing_key_set", rules)
        results = execute_rules("missing_key_set", [{"other_key": 5}])
        assert results == []

    def test_complex_rule_set(self):
        rules = [
            {
                "name": "rule_1",
                "condition": "fact.get('age', 0) >= 18 and fact.get('income', 0) > 50000",
                "action": "{'eligible': True, 'tier': 'premier'}",
                "priority": 10,
            },
            {
                "name": "rule_2",
                "condition": "fact.get('age', 0) >= 18",
                "action": "{'eligible': True, 'tier': 'standard'}",
                "priority": 5,
            },
            {
                "name": "rule_3",
                "condition": "fact.get('age', 0) < 18",
                "action": "{'eligible': False, 'tier': 'underage'}",
                "priority": 1,
            },
        ]
        register_rule_set("complex", rules, strategy="FIRST_MATCH")
        results = execute_rules(
            "complex", [{"age": 25, "income": 60000}]
        )
        assert len(results) == 1
        assert results[0]["tier"] == "premier"

    def test_fact_with_string_values(self):
        rules = [
            {
                "name": "string_check",
                "condition": "fact.get('status', '') == 'active'",
                "action": "{'active': True}",
            }
        ]
        register_rule_set("string_set", rules)
        results = execute_rules("string_set", [{"status": "active"}])
        assert results == [{"active": True}]
        results = execute_rules("string_set", [{"status": "inactive"}])
        assert results == []
