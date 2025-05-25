"""
Test suite for Machine Rules Engine
"""

import pytest


class TestRule:
    """Test the Rule class."""

    def test_rule_creation(self):
        from machine_rules.api.execution_set import Rule

        def condition(fact):
            return fact.get('value', 0) > 10

        def action(fact):
            return {'result': 'high'}

        rule = Rule(
            name="test_rule", condition=condition, action=action, priority=5
        )

        assert rule.name == "test_rule"
        assert rule.priority == 5
        assert rule.condition({'value': 15}) is True
        assert rule.condition({'value': 5}) is False
        assert rule.action({'value': 15}) == {'result': 'high'}


class TestRuleExecutionSet:
    """Test the RuleExecutionSet class."""

    def test_rule_execution_set_creation(self):
        from machine_rules.api.execution_set import (
            Rule, RuleExecutionSet
        )

        def condition(fact):
            return fact.get('value', 0) > 10

        def action(fact):
            return {'result': 'high'}

        rule = Rule(name="test_rule", condition=condition, action=action)
        execution_set = RuleExecutionSet(name="test_set", rules=[rule])

        assert execution_set.get_name() == "test_set"
        assert len(execution_set.get_rules()) == 1
        assert execution_set.get_rules()[0].name == "test_rule"

    def test_rule_priority_sorting(self):
        from machine_rules.api.execution_set import (
            Rule, RuleExecutionSet
        )

        rule1 = Rule(
            name="low_priority", condition=lambda f: True,
            action=lambda f: 1, priority=1
        )
        rule2 = Rule(
            name="high_priority", condition=lambda f: True,
            action=lambda f: 2, priority=10
        )
        rule3 = Rule(
            name="medium_priority", condition=lambda f: True,
            action=lambda f: 3, priority=5
        )

        execution_set = RuleExecutionSet(
            name="test_set", rules=[rule1, rule2, rule3]
        )
        rules = execution_set.get_rules()

        assert rules[0].name == "high_priority"
        assert rules[1].name == "medium_priority"
        assert rules[2].name == "low_priority"


class TestMachineAdapter:
    """Test the Machine adapter implementation."""

    def test_machine_rule_session(self):
        from machine_rules.adapters.machine_adapter import (
            MachineRuleSession
        )
        from machine_rules.api.execution_set import (
            Rule, RuleExecutionSet
        )

        def condition(fact):
            return fact.get('income', 0) > 50000

        def action(fact):
            return {'category': 'high_income'}

        rule = Rule(name="income_rule", condition=condition, action=action)
        execution_set = RuleExecutionSet(name="income_rules", rules=[rule])

        session = MachineRuleSession(execution_set)
        session.add_facts([{'income': 60000}, {'income': 30000}])

        results = session.execute()

        assert len(results) == 1
        assert results[0] == {'category': 'high_income'}

        session.close()

    def test_machine_rule_administrator(self):
        from machine_rules.adapters.machine_adapter import (
            MachineRuleAdministrator
        )
        from machine_rules.api.execution_set import (
            Rule, RuleExecutionSet
        )

        admin = MachineRuleAdministrator()

        rule = Rule(
            name="test_rule", condition=lambda f: True,
            action=lambda f: 'result'
        )
        execution_set = RuleExecutionSet(name="test_set", rules=[rule])

        admin.register_rule_execution_set("test_uri", execution_set)

        registrations = admin.get_registrations()
        assert "test_uri" in registrations
        assert registrations["test_uri"].get_name() == "test_set"

        admin.deregister_rule_execution_set("test_uri")
        registrations = admin.get_registrations()
        assert "test_uri" not in registrations

    def test_machine_rule_runtime(self):
        from machine_rules.adapters.machine_adapter import (
            MachineRuleAdministrator, MachineRuleRuntime
        )
        from machine_rules.api.execution_set import (
            Rule, RuleExecutionSet
        )

        admin = MachineRuleAdministrator()
        runtime = MachineRuleRuntime(admin)

        rule = Rule(
            name="test_rule", condition=lambda f: True,
            action=lambda f: 'result'
        )
        execution_set = RuleExecutionSet(name="test_set", rules=[rule])
        admin.register_rule_execution_set("test_uri", execution_set)

        session = runtime.create_rule_session("test_uri")
        assert session is not None

        registrations = runtime.get_registrations()
        assert "test_uri" in registrations

        # Test error case
        with pytest.raises(ValueError):
            runtime.create_rule_session("nonexistent_uri")


class TestRuleServiceProvider:
    """Test the rule service provider."""

    def test_machine_rule_service_provider(self):
        from machine_rules.adapters.machine_adapter import (
            MachineRuleServiceProvider
        )

        provider = MachineRuleServiceProvider()

        admin = provider.get_rule_administrator()
        runtime = provider.get_rule_runtime()

        assert admin is not None
        assert runtime is not None

        # Test that they're properly connected
        from machine_rules.api.execution_set import (
            Rule, RuleExecutionSet
        )

        rule = Rule(
            name="test_rule", condition=lambda f: True,
            action=lambda f: 'result'
        )
        execution_set = RuleExecutionSet(name="test_set", rules=[rule])

        admin.register_rule_execution_set("test_uri", execution_set)
        session = runtime.create_rule_session("test_uri")

        assert session is not None


class TestRuleServiceProviderManager:
    """Test the rule service provider manager."""

    def test_provider_registration(self):
        from machine_rules.api.registry import (
            RuleServiceProviderManager
        )
        from machine_rules.adapters.machine_adapter import (
            MachineRuleServiceProvider
        )

        # Clear any existing registrations
        provider = MachineRuleServiceProvider()
        RuleServiceProviderManager.register("test_provider", provider)

        retrieved_provider = RuleServiceProviderManager.get("test_provider")
        assert retrieved_provider is provider

        uris = RuleServiceProviderManager.get_registered_uris()
        assert "test_provider" in uris

        RuleServiceProviderManager.deregister("test_provider")
        retrieved_provider = RuleServiceProviderManager.get("test_provider")
        assert retrieved_provider is None


if __name__ == "__main__":
    pytest.main([__file__])
