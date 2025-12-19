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

        # Test error case - now raises RuleValidationError
        from machine_rules.api.exceptions import RuleValidationError
        with pytest.raises(RuleValidationError):
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


class TestLoggingInsteadOfPrint:
    """Test that logging is used instead of print (Phase 2, Task 2.3)."""

    def test_rule_execution_errors_use_logging(self, caplog):
        """Errors during rule execution should use logging, not print."""
        import logging
        from machine_rules.adapters.machine_adapter import (
            MachineRuleAdministrator, MachineRuleRuntime
        )
        from machine_rules.api.execution_set import Rule, RuleExecutionSet

        # Create a rule that will raise an exception
        def bad_condition(fact):
            raise ValueError("Intentional error for testing")

        rule = Rule(
            name="error_rule",
            condition=bad_condition,
            action=lambda f: {'result': 'pass'},
            priority=1
        )
        execution_set = RuleExecutionSet(name="test_set", rules=[rule])
        
        admin = MachineRuleAdministrator()
        admin.register_rule_execution_set("test_uri", execution_set)
        runtime = MachineRuleRuntime(admin)
        
        session = runtime.create_rule_session("test_uri")
        session.add_facts([{'value': 15}])
        
        # Execute - should log error
        with caplog.at_level(logging.ERROR):
            session.execute()
        
        # Should have logged the error
        assert "Error executing rule error_rule" in caplog.text
        assert "Intentional error for testing" in caplog.text
        
        session.close()


class TestStatelessSessionBehavior:
    """Test stateless vs stateful session behavior (Phase 2, Task 2.1)."""

    def test_stateless_session_clears_facts_after_execute(self):
        """Stateless sessions should not retain facts after execute."""
        from machine_rules.adapters.machine_adapter import (
            MachineRuleAdministrator, MachineRuleRuntime
        )
        from machine_rules.api.execution_set import Rule, RuleExecutionSet

        # Setup
        rule = Rule(
            name="test_rule",
            condition=lambda f: f.get('value', 0) > 10,
            action=lambda f: {'result': 'pass'},
            priority=1
        )
        execution_set = RuleExecutionSet(name="test_set", rules=[rule])
        
        admin = MachineRuleAdministrator()
        admin.register_rule_execution_set("test_uri", execution_set)
        runtime = MachineRuleRuntime(admin)
        
        # Create stateless session
        session = runtime.create_rule_session("test_uri", stateless=True)
        session.add_facts([{'value': 15}])
        
        # Execute
        results = session.execute()
        assert len(results) == 1
        
        # Facts should be cleared after execute
        assert len(session.facts) == 0
        
        session.close()

    def test_stateful_session_retains_facts(self):
        """Stateful sessions should retain facts after execute."""
        from machine_rules.adapters.machine_adapter import (
            MachineRuleAdministrator, MachineRuleRuntime
        )
        from machine_rules.api.execution_set import Rule, RuleExecutionSet

        # Setup
        rule = Rule(
            name="test_rule",
            condition=lambda f: f.get('value', 0) > 10,
            action=lambda f: {'result': 'pass'},
            priority=1
        )
        execution_set = RuleExecutionSet(name="test_set", rules=[rule])
        
        admin = MachineRuleAdministrator()
        admin.register_rule_execution_set("test_uri", execution_set)
        runtime = MachineRuleRuntime(admin)
        
        # Create stateful session (default)
        session = runtime.create_rule_session("test_uri", stateless=False)
        session.add_facts([{'value': 15}])
        
        # Execute
        results = session.execute()
        assert len(results) == 1
        
        # Facts should be retained
        assert len(session.facts) == 1
        
        session.close()

    def test_stateless_parameter_propagated(self):
        """Stateless flag should be passed to session."""
        from machine_rules.adapters.machine_adapter import (
            MachineRuleAdministrator, MachineRuleRuntime
        )
        from machine_rules.api.execution_set import Rule, RuleExecutionSet

        # Setup
        rule = Rule(name="test", condition=lambda f: True, action=lambda f: {})
        execution_set = RuleExecutionSet(name="test_set", rules=[rule])
        
        admin = MachineRuleAdministrator()
        admin.register_rule_execution_set("test_uri", execution_set)
        runtime = MachineRuleRuntime(admin)
        
        # Test stateless=True
        session = runtime.create_rule_session("test_uri", stateless=True)
        assert hasattr(session, 'stateless')
        assert session.stateless is True
        session.close()
        
        # Test stateless=False (explicit)
        session = runtime.create_rule_session("test_uri", stateless=False)
        assert session.stateless is False
        session.close()
        
        # Test default (should be stateful for backward compatibility)
        session = runtime.create_rule_session("test_uri")
        assert session.stateless is False
        session.close()


class TestExecutionStrategy:
    """Test execution strategy (FIRST_MATCH vs ALL_MATCHES)."""

    def test_all_matches_strategy_returns_all_results(self):
        """ALL_MATCHES strategy should execute all matching rules."""
        from machine_rules.adapters.machine_adapter import (
            MachineRuleAdministrator, MachineRuleRuntime
        )
        from machine_rules.api.execution_set import Rule, RuleExecutionSet

        # Create multiple rules that all match
        rule1 = Rule(
            name="rule1",
            condition=lambda f: f.get('value', 0) > 5,
            action=lambda f: {'result': 'rule1', 'priority': 10},
            priority=10
        )
        rule2 = Rule(
            name="rule2",
            condition=lambda f: f.get('value', 0) > 5,
            action=lambda f: {'result': 'rule2', 'priority': 5},
            priority=5
        )
        rule3 = Rule(
            name="rule3",
            condition=lambda f: f.get('value', 0) > 5,
            action=lambda f: {'result': 'rule3', 'priority': 1},
            priority=1
        )
        
        # ALL_MATCHES is default behavior
        execution_set = RuleExecutionSet(
            name="test_set",
            rules=[rule1, rule2, rule3],
            properties={'strategy': 'ALL_MATCHES'}
        )
        
        admin = MachineRuleAdministrator()
        admin.register_rule_execution_set("test_uri", execution_set)
        runtime = MachineRuleRuntime(admin)
        
        session = runtime.create_rule_session("test_uri")
        session.add_facts([{'value': 10}])
        results = session.execute()
        
        # All 3 rules should match and execute
        assert len(results) == 3
        assert results[0]['result'] == 'rule1'  # Highest priority first
        assert results[1]['result'] == 'rule2'
        assert results[2]['result'] == 'rule3'
        
        session.close()

    def test_first_match_strategy_stops_after_first_match(self):
        """FIRST_MATCH strategy should stop after first matching rule per fact."""
        from machine_rules.adapters.machine_adapter import (
            MachineRuleAdministrator, MachineRuleRuntime
        )
        from machine_rules.api.execution_set import Rule, RuleExecutionSet

        # Create multiple rules that all match
        rule1 = Rule(
            name="rule1",
            condition=lambda f: f.get('value', 0) > 5,
            action=lambda f: {'result': 'rule1', 'priority': 10},
            priority=10
        )
        rule2 = Rule(
            name="rule2",
            condition=lambda f: f.get('value', 0) > 5,
            action=lambda f: {'result': 'rule2', 'priority': 5},
            priority=5
        )
        rule3 = Rule(
            name="rule3",
            condition=lambda f: f.get('value', 0) > 5,
            action=lambda f: {'result': 'rule3', 'priority': 1},
            priority=1
        )
        
        execution_set = RuleExecutionSet(
            name="test_set",
            rules=[rule1, rule2, rule3],
            properties={'strategy': 'FIRST_MATCH'}
        )
        
        admin = MachineRuleAdministrator()
        admin.register_rule_execution_set("test_uri", execution_set)
        runtime = MachineRuleRuntime(admin)
        
        session = runtime.create_rule_session("test_uri")
        session.add_facts([{'value': 10}])
        results = session.execute()
        
        # Only the highest priority rule should execute
        assert len(results) == 1
        assert results[0]['result'] == 'rule1'  # Highest priority only
        
        session.close()

    def test_default_strategy_is_all_matches(self):
        """If no strategy specified, default should be ALL_MATCHES."""
        from machine_rules.adapters.machine_adapter import (
            MachineRuleAdministrator, MachineRuleRuntime
        )
        from machine_rules.api.execution_set import Rule, RuleExecutionSet

        # Create multiple matching rules
        rule1 = Rule(
            name="rule1",
            condition=lambda f: True,
            action=lambda f: {'result': 'rule1'},
            priority=10
        )
        rule2 = Rule(
            name="rule2",
            condition=lambda f: True,
            action=lambda f: {'result': 'rule2'},
            priority=5
        )
        
        # No strategy property specified
        execution_set = RuleExecutionSet(
            name="test_set",
            rules=[rule1, rule2]
        )
        
        admin = MachineRuleAdministrator()
        admin.register_rule_execution_set("test_uri", execution_set)
        runtime = MachineRuleRuntime(admin)
        
        session = runtime.create_rule_session("test_uri")
        session.add_facts([{'value': 1}])
        results = session.execute()
        
        # Both rules should execute (backward compatible behavior)
        assert len(results) == 2
        
        session.close()


class TestCustomExceptions:
    """Test custom exception classes."""

    def test_custom_exceptions_exist(self):
        """Custom exception classes should be defined."""
        from machine_rules.api.exceptions import (
            RuleEngineError,
            RuleExecutionError,
            RuleValidationError,
            SessionError
        )
        
        # Verify inheritance
        assert issubclass(RuleExecutionError, RuleEngineError)
        assert issubclass(RuleValidationError, RuleEngineError)
        assert issubclass(SessionError, RuleEngineError)

    def test_session_closed_error_on_execute(self):
        """Closed session should raise SessionError on execute."""
        from machine_rules.adapters.machine_adapter import (
            MachineRuleAdministrator, MachineRuleRuntime
        )
        from machine_rules.api.execution_set import Rule, RuleExecutionSet
        from machine_rules.api.exceptions import SessionError

        rule = Rule(name="test", condition=lambda f: True, action=lambda f: {})
        execution_set = RuleExecutionSet(name="test_set", rules=[rule])
        
        admin = MachineRuleAdministrator()
        admin.register_rule_execution_set("test_uri", execution_set)
        runtime = MachineRuleRuntime(admin)
        
        session = runtime.create_rule_session("test_uri")
        session.close()
        
        with pytest.raises(SessionError, match="closed"):
            session.execute()

    def test_session_closed_error_on_add_facts(self):
        """Closed session should raise SessionError on add_facts."""
        from machine_rules.adapters.machine_adapter import (
            MachineRuleAdministrator, MachineRuleRuntime
        )
        from machine_rules.api.execution_set import Rule, RuleExecutionSet
        from machine_rules.api.exceptions import SessionError

        rule = Rule(name="test", condition=lambda f: True, action=lambda f: {})
        execution_set = RuleExecutionSet(name="test_set", rules=[rule])
        
        admin = MachineRuleAdministrator()
        admin.register_rule_execution_set("test_uri", execution_set)
        runtime = MachineRuleRuntime(admin)
        
        session = runtime.create_rule_session("test_uri")
        session.close()
        
        with pytest.raises(SessionError, match="closed"):
            session.add_facts([{'value': 1}])

    def test_session_closed_error_on_reset(self):
        """Closed session should raise SessionError on reset."""
        from machine_rules.adapters.machine_adapter import (
            MachineRuleAdministrator, MachineRuleRuntime
        )
        from machine_rules.api.execution_set import Rule, RuleExecutionSet
        from machine_rules.api.exceptions import SessionError

        rule = Rule(name="test", condition=lambda f: True, action=lambda f: {})
        execution_set = RuleExecutionSet(name="test_set", rules=[rule])
        
        admin = MachineRuleAdministrator()
        admin.register_rule_execution_set("test_uri", execution_set)
        runtime = MachineRuleRuntime(admin)
        
        session = runtime.create_rule_session("test_uri")
        session.close()
        
        with pytest.raises(SessionError, match="closed"):
            session.reset()


class TestInputValidation:
    """Test input validation in runtime methods."""

    def test_runtime_validates_uri_exists(self):
        """Runtime should validate URI is registered."""
        from machine_rules.adapters.machine_adapter import (
            MachineRuleAdministrator, MachineRuleRuntime
        )
        from machine_rules.api.exceptions import RuleValidationError

        admin = MachineRuleAdministrator()
        runtime = MachineRuleRuntime(admin)
        
        with pytest.raises(RuleValidationError, match="not found|registered"):
            runtime.create_rule_session("nonexistent_uri")

    def test_session_validates_facts_type(self):
        """Session should validate facts is a list."""
        from machine_rules.adapters.machine_adapter import (
            MachineRuleAdministrator, MachineRuleRuntime
        )
        from machine_rules.api.execution_set import Rule, RuleExecutionSet
        from machine_rules.api.exceptions import RuleValidationError

        rule = Rule(name="test", condition=lambda f: True, action=lambda f: {})
        execution_set = RuleExecutionSet(name="test_set", rules=[rule])
        
        admin = MachineRuleAdministrator()
        admin.register_rule_execution_set("test_uri", execution_set)
        runtime = MachineRuleRuntime(admin)
        
        session = runtime.create_rule_session("test_uri")
        
        with pytest.raises(RuleValidationError, match="must be a list"):
            session.add_facts("not a list")
        
        with pytest.raises(RuleValidationError, match="must be a list"):
            session.add_facts({"key": "value"})
        
        session.close()

    def test_admin_validates_execution_set_type(self):
        """Admin should validate execution set parameter."""
        from machine_rules.adapters.machine_adapter import MachineRuleAdministrator
        from machine_rules.api.exceptions import RuleValidationError

        admin = MachineRuleAdministrator()
        
        with pytest.raises(RuleValidationError, match="RuleExecutionSet"):
            admin.register_rule_execution_set("uri", "not an execution set")
        
        with pytest.raises(RuleValidationError, match="RuleExecutionSet"):
            admin.register_rule_execution_set("uri", None)
        
        with pytest.raises(RuleValidationError, match="RuleExecutionSet"):
            admin.register_rule_execution_set("uri", {"name": "test"})

    def test_admin_validates_uri_not_empty(self):
        """Admin should validate URI is not empty."""
        from machine_rules.adapters.machine_adapter import MachineRuleAdministrator
        from machine_rules.api.execution_set import Rule, RuleExecutionSet
        from machine_rules.api.exceptions import RuleValidationError

        admin = MachineRuleAdministrator()
        rule = Rule(name="test", condition=lambda f: True, action=lambda f: {})
        execution_set = RuleExecutionSet(name="test_set", rules=[rule])
        
        with pytest.raises(RuleValidationError, match="URI|empty"):
            admin.register_rule_execution_set("", execution_set)


class TestThreadSafety:
    """Test thread safety for concurrent operations."""

    def test_concurrent_provider_registration(self):
        """Multiple threads can safely register providers."""
        import threading
        from machine_rules.adapters.machine_adapter import MachineRuleServiceProvider
        from machine_rules.api.registry import RuleServiceProviderManager

        # Clear any existing registrations
        for uri in list(RuleServiceProviderManager.get_registered_uris()):
            RuleServiceProviderManager.deregister(uri)

        results = []
        errors = []

        def register_provider(name):
            try:
                provider = MachineRuleServiceProvider()
                RuleServiceProviderManager.register(name, provider)
                results.append(name)
            except Exception as e:
                errors.append((name, str(e)))

        # Create 50 threads to register providers concurrently
        threads = [
            threading.Thread(target=register_provider, args=(f"provider_{i}",))
            for i in range(50)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All providers should be registered without errors
        assert len(errors) == 0, f"Registration errors: {errors}"
        assert len(RuleServiceProviderManager.get_registered_uris()) == 50
        assert len(results) == 50

    def test_concurrent_rule_registration(self):
        """Multiple threads can safely register rules."""
        import threading
        from machine_rules.adapters.machine_adapter import MachineRuleAdministrator
        from machine_rules.api.execution_set import Rule, RuleExecutionSet

        admin = MachineRuleAdministrator()
        errors = []
        results = []

        def register_rules(rule_set_id):
            try:
                rule = Rule(
                    name=f"rule_{rule_set_id}",
                    condition=lambda f: True,
                    action=lambda f: {'id': rule_set_id},
                    priority=rule_set_id
                )
                execution_set = RuleExecutionSet(
                    name=f"set_{rule_set_id}",
                    rules=[rule]
                )
                admin.register_rule_execution_set(f"uri_{rule_set_id}", execution_set)
                results.append(rule_set_id)
            except Exception as e:
                errors.append((rule_set_id, str(e)))

        # Create 50 threads to register rules concurrently
        threads = [
            threading.Thread(target=register_rules, args=(i,))
            for i in range(50)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All rules should be registered without errors
        assert len(errors) == 0, f"Registration errors: {errors}"
        assert len(admin.get_registrations()) == 50
        assert len(results) == 50

    def test_concurrent_session_operations(self):
        """Multiple threads can safely create and use sessions."""
        import threading
        from machine_rules.adapters.machine_adapter import (
            MachineRuleAdministrator, MachineRuleRuntime
        )
        from machine_rules.api.execution_set import Rule, RuleExecutionSet

        # Setup
        rule = Rule(
            name="concurrent_rule",
            condition=lambda f: f.get('value', 0) > 5,
            action=lambda f: {'result': f['value'] * 2},
            priority=1
        )
        execution_set = RuleExecutionSet(name="test_set", rules=[rule])
        
        admin = MachineRuleAdministrator()
        admin.register_rule_execution_set("test_uri", execution_set)
        runtime = MachineRuleRuntime(admin)

        errors = []
        results = []

        def execute_rules(thread_id):
            try:
                session = runtime.create_rule_session("test_uri", stateless=True)
                session.add_facts([{'value': thread_id}])
                result = session.execute()
                session.close()
                results.append((thread_id, result))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Create 30 threads to execute rules concurrently
        threads = [
            threading.Thread(target=execute_rules, args=(i,))
            for i in range(30)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All executions should complete without errors
        assert len(errors) == 0, f"Execution errors: {errors}"
        assert len(results) == 30


if __name__ == "__main__":
    pytest.main([__file__])
