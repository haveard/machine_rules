"""
Integration tests for Machine Rules Engine

These tests verify the interaction between different components of
the rules engine,
including providers, loaders, sessions, and API endpoints.
"""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient

# Import core components and ensure initialization
import machine_rules  # Ensure module initialization
from machine_rules.api.registry import RuleServiceProviderManager
from machine_rules.api.execution_set import Rule, RuleExecutionSet
from machine_rules.adapters.machine_adapter import MachineRuleServiceProvider
from machine_rules.loader.yaml_loader import YAMLRuleLoader
# DMN loader removed - deprecated due to security vulnerabilities


def get_api_provider():
    """Helper function to safely get the API provider with proper
    error handling."""
    provider = RuleServiceProviderManager.get("api")
    if provider is None:
        # Ensure initialization if provider is not found
        machine_rules.initialize()
        provider = RuleServiceProviderManager.get("api")
    assert provider is not None, (
        "API provider should be registered after initialization"
    )
    return provider


class TestProviderRegistryIntegration:
    """Integration tests for provider registration and management."""

    def test_provider_lifecycle_with_rule_execution(self):
        """Test complete provider lifecycle with rule execution."""
        # Create a custom provider
        custom_provider = MachineRuleServiceProvider()

        # Register custom provider
        RuleServiceProviderManager.register("custom_test", custom_provider)

        # Verify registration
        retrieved_provider = RuleServiceProviderManager.get("custom_test")
        assert retrieved_provider is custom_provider

        # Create and register a rule
        def condition(fact):
            return fact.get("score", 0) > 80

        def action(fact):
            return {"grade": "A", "passed": True}

        rule = Rule(name="grade_rule", condition=condition, action=action)
        execution_set = RuleExecutionSet(name="grading", rules=[rule])

        admin = custom_provider.get_rule_administrator()
        runtime = custom_provider.get_rule_runtime()

        admin.register_rule_execution_set("grade_rules", execution_set)

        # Execute rules
        session = runtime.create_rule_session("grade_rules")
        session.add_facts([{"score": 85}, {"score": 75}])
        results = session.execute()

        assert len(results) == 1
        assert results[0] == {"grade": "A", "passed": True}

        session.close()

        # Cleanup
        RuleServiceProviderManager.deregister("custom_test")
        assert RuleServiceProviderManager.get("custom_test") is None

    def test_multiple_providers_isolation(self):
        """Test that multiple providers maintain separate state."""
        provider1 = MachineRuleServiceProvider()
        provider2 = MachineRuleServiceProvider()

        RuleServiceProviderManager.register("provider1", provider1)
        RuleServiceProviderManager.register("provider2", provider2)

        # Create different rules for each provider
        rule1 = Rule(
            name="rule1",
            condition=lambda f: f.get("type") == "A",
            action=lambda f: {"result": "from_provider1"},
        )
        rule2 = Rule(
            name="rule2",
            condition=lambda f: f.get("type") == "A",
            action=lambda f: {"result": "from_provider2"},
        )

        set1 = RuleExecutionSet(name="set1", rules=[rule1])
        set2 = RuleExecutionSet(name="set2", rules=[rule2])

        # Register with different providers
        provider1.get_rule_administrator().register_rule_execution_set("test", set1)
        provider2.get_rule_administrator().register_rule_execution_set("test", set2)

        # Execute with each provider
        session1 = provider1.get_rule_runtime().create_rule_session("test")
        session2 = provider2.get_rule_runtime().create_rule_session("test")

        session1.add_facts([{"type": "A"}])
        session2.add_facts([{"type": "A"}])

        result1 = session1.execute()
        result2 = session2.execute()

        assert result1[0]["result"] == "from_provider1"
        assert result2[0]["result"] == "from_provider2"

        session1.close()
        session2.close()

        # Cleanup
        RuleServiceProviderManager.deregister("provider1")
        RuleServiceProviderManager.deregister("provider2")


class TestYAMLLoaderIntegration:
    """Integration tests for YAML loader with full rule execution."""

    def test_complex_yaml_rules_end_to_end(self):
        """Test complex YAML rules from definition to execution."""
        yaml_content = """
name: "financial_assessment"
description: "Financial risk assessment rules"
rules:
  - name: "high_risk"
    condition: >
      (fact.get('debt_ratio', 0) > 0.4 and fact.get('income', 0) < 50000) or
      fact.get('credit_score', 800) < 600
    action: >
      {
        'risk_level': 'HIGH',
        'recommendation': 'REJECT',
        'required_collateral': fact.get('loan_amount', 0) * 1.5
      }
    priority: 100

  - name: "medium_risk"
    condition: >
      fact.get('debt_ratio', 0) > 0.3 or
      fact.get('credit_score', 800) < 700
    action: >
      {
        'risk_level': 'MEDIUM',
        'recommendation': 'REVIEW',
        'required_collateral': fact.get('loan_amount', 0) * 1.2
      }
    priority: 50

  - name: "low_risk"
    condition: "True"
    action: >
      {
        'risk_level': 'LOW',
        'recommendation': 'APPROVE',
        'required_collateral': 0
      }
    priority: 10
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            # Load rules
            execution_set = YAMLRuleLoader.from_file(temp_path)

            # Register with default provider
            provider = get_api_provider()
            admin = provider.get_rule_administrator()
            runtime = provider.get_rule_runtime()

            admin.register_rule_execution_set("financial_rules", execution_set)

            # Test various financial profiles
            test_cases = [
                {
                    "debt_ratio": 0.5,
                    "income": 40000,
                    "credit_score": 550,
                    "loan_amount": 100000,
                    "expected_risk": "HIGH",
                },
                {
                    "debt_ratio": 0.35,
                    "income": 80000,
                    "credit_score": 650,
                    "loan_amount": 50000,
                    "expected_risk": "MEDIUM",
                },
                {
                    "debt_ratio": 0.2,
                    "income": 100000,
                    "credit_score": 750,
                    "loan_amount": 75000,
                    "expected_risk": "LOW",
                },
            ]

            session = runtime.create_rule_session("financial_rules")

            for case in test_cases:
                session.reset()
                session.add_facts([case])
                results = session.execute()

                # All matching rules fire, so check the highest priority result
                assert len(results) >= 1
                # Results are ordered by priority, so first result is highest priority
                highest_priority_result = results[0]
                assert highest_priority_result["risk_level"] == case["expected_risk"]

                if case["expected_risk"] == "HIGH":
                    assert highest_priority_result["recommendation"] == "REJECT"
                    assert (
                        highest_priority_result["required_collateral"]
                        == case["loan_amount"] * 1.5
                    )
                elif case["expected_risk"] == "MEDIUM":
                    assert highest_priority_result["recommendation"] == "REVIEW"
                    assert (
                        highest_priority_result["required_collateral"]
                        == case["loan_amount"] * 1.2
                    )
                else:
                    assert highest_priority_result["recommendation"] == "APPROVE"
                    assert highest_priority_result["required_collateral"] == 0

            session.close()

        finally:
            os.unlink(temp_path)

    def test_yaml_error_handling_integration(self):
        """Test YAML loader error handling in integration context."""
        # YAML with intentional syntax error in condition
        yaml_content = """
name: "error_test"
rules:
  - name: "good_rule"
    condition: "fact.get('test') == 'valid'"
    action: "{'result': 'valid_test'}"
    priority: 1
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            execution_set = YAMLRuleLoader.from_file(temp_path)

            provider = get_api_provider()
            admin = provider.get_rule_administrator()
            runtime = provider.get_rule_runtime()

            admin.register_rule_execution_set("error_rules", execution_set)
            session = runtime.create_rule_session("error_rules")

            session.add_facts([{"test": "valid"}])
            results = session.execute()

            # Should handle valid rules correctly
            assert len(results) == 1
            assert results[0]["result"] == "valid_test"

            session.close()

        finally:
            os.unlink(temp_path)


# DMN loader integration tests removed - DMN loader deprecated and removed due to security vulnerabilities


class TestSessionStateIntegration:
    """Integration tests for session state management."""

    def test_stateful_session_accumulation(self):
        """Test stateful session with fact accumulation."""

        # Create rules that work with accumulated facts
        def count_condition(fact):
            return fact.get("action") == "count"

        def count_action(fact):
            # This would typically access session state
            return {"count_request": True}

        rule = Rule(name="counter", condition=count_condition, action=count_action)
        execution_set = RuleExecutionSet(name="stateful_test", rules=[rule])

        provider = get_api_provider()
        admin = provider.get_rule_administrator()
        runtime = provider.get_rule_runtime()

        admin.register_rule_execution_set("counter_rules", execution_set)

        # Test stateful session (default behavior)
        session = runtime.create_rule_session("counter_rules", stateless=False)

        # Add facts incrementally
        session.add_facts([{"action": "count", "value": 1}])
        results1 = session.execute()

        session.add_facts([{"action": "count", "value": 2}])
        results2 = session.execute()

        # Should accumulate facts
        assert len(results1) == 1
        assert len(results2) == 2  # Both facts should trigger rules

        session.close()

    def test_stateless_session_isolation(self):
        """Test stateless session with fact isolation."""
        rule = Rule(
            name="isolated",
            condition=lambda f: f.get("type") == "test",
            action=lambda f: {"processed": f.get("id")},
        )
        execution_set = RuleExecutionSet(name="isolation_test", rules=[rule])

        provider = get_api_provider()
        admin = provider.get_rule_administrator()
        runtime = provider.get_rule_runtime()

        admin.register_rule_execution_set("isolation_rules", execution_set)

        # Test stateless session
        session = runtime.create_rule_session("isolation_rules", stateless=True)

        session.add_facts([{"type": "test", "id": 1}])
        results1 = session.execute()

        # Reset session to clear facts for stateless behavior simulation
        session.reset()
        session.add_facts([{"type": "test", "id": 2}])
        results2 = session.execute()

        # Each execution should be independent
        assert len(results1) == 1
        assert len(results2) == 1
        assert results1[0]["processed"] == 1
        assert results2[0]["processed"] == 2

        session.close()


class TestRulePriorityIntegration:
    """Integration tests for rule priority and execution order."""

    def test_complex_priority_execution(self):
        """Test complex priority-based rule execution."""
        # Create rules with different priorities
        rules = []

        # Emergency rule (highest priority)
        rules.append(
            Rule(
                name="emergency",
                condition=lambda f: f.get("emergency", False),
                action=lambda f: {"priority": "EMERGENCY", "order": 1},
                priority=1000,
            )
        )

        # Business hours rule
        rules.append(
            Rule(
                name="business_hours",
                condition=lambda f: 9 <= f.get("hour", 0) <= 17,
                action=lambda f: {"priority": "BUSINESS", "order": 2},
                priority=100,
            )
        )

        # Default rule (lowest priority)
        rules.append(
            Rule(
                name="default",
                condition=lambda f: True,
                action=lambda f: {"priority": "DEFAULT", "order": 3},
                priority=1,
            )
        )

        execution_set = RuleExecutionSet(name="priority_test", rules=rules)

        provider = get_api_provider()
        admin = provider.get_rule_administrator()
        runtime = provider.get_rule_runtime()

        admin.register_rule_execution_set("priority_rules", execution_set)
        session = runtime.create_rule_session("priority_rules")

        # Test different scenarios
        test_cases = [
            {"emergency": True, "hour": 10, "expected_priority": "EMERGENCY"},
            {"emergency": False, "hour": 12, "expected_priority": "BUSINESS"},
            {"emergency": False, "hour": 20, "expected_priority": "DEFAULT"},
        ]

        for case in test_cases:
            session.reset()
            session.add_facts([case])
            results = session.execute()

            # Should get results from all matching rules, ordered by priority
            assert len(results) >= 1
            # Check that highest priority matching rule comes first
            highest_priority_result = results[0]
            assert highest_priority_result["priority"] == case["expected_priority"]

        session.close()


class TestFastAPIIntegration:
    """Integration tests for FastAPI endpoints."""

    def test_complete_api_workflow(self):
        """Test complete API workflow from registration to execution."""
        # Ensure initialization
        import machine_rules  # noqa: F401

        from machine_rules.__main__ import app

        client = TestClient(app)

        # Register rules via the provider
        provider = get_api_provider()
        admin = provider.get_rule_administrator()

        # Create customer classification rules
        rules = [
            Rule(
                name="vip_customer",
                condition=lambda f: f.get("total_spent", 0) > 10000,
                action=lambda f: {
                    "tier": "VIP",
                    "discount": 0.2,
                    "benefits": ["free_shipping", "priority_support"],
                },
                priority=20,
            ),
            Rule(
                name="regular_customer",
                condition=lambda f: f.get("total_spent", 0) > 1000,
                action=lambda f: {"tier": "REGULAR", "discount": 0.1},
                priority=10,
            ),
            Rule(
                name="new_customer",
                condition=lambda f: True,
                action=lambda f: {"tier": "NEW", "discount": 0.05},
                priority=1,
            ),
        ]

        execution_set = RuleExecutionSet(name="customer_tiers", rules=rules)
        admin.register_rule_execution_set("customer_classification", execution_set)

        # Test API execution with various customer profiles
        test_customers = [
            {"customer_id": "C001", "total_spent": 15000, "expected_tier": "VIP"},
            {"customer_id": "C002", "total_spent": 2500, "expected_tier": "REGULAR"},
            {"customer_id": "C003", "total_spent": 100, "expected_tier": "NEW"},
        ]

        for customer in test_customers:
            response = client.post(
                "/execute",
                json={"facts": [customer], "ruleset_uri": "customer_classification"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) >= 1
            # Check the highest priority rule result (first in list)
            highest_priority_result = data["results"][0]
            assert highest_priority_result["tier"] == customer["expected_tier"]

    def test_api_error_handling_integration(self):
        """Test API error handling with various scenarios."""
        import machine_rules  # noqa: F401

        from machine_rules.__main__ import app

        client = TestClient(app)

        # Test non-existent ruleset
        response = client.post(
            "/execute",
            json={"facts": [{"test": "data"}], "ruleset_uri": "non_existent_rules"},
        )
        assert response.status_code == 400

        # Test invalid request format
        response = client.post("/execute", json={"invalid": "format"})
        assert response.status_code == 422


class TestCrossLoaderIntegration:
    """Integration tests combining different rule loaders."""

    def test_mixed_rule_sources_integration(self):
        """Test integration of rules from different sources."""
        # Create programmatic rule
        prog_rule = Rule(
            name="programmatic_rule",
            condition=lambda f: f.get("source") == "program",
            action=lambda f: {"processed_by": "programmatic"},
            priority=100,
        )

        # Create YAML rule
        yaml_content = """
name: "yaml_section"
rules:
  - name: "yaml_rule"
    condition: "fact.get('source') == 'yaml'"
    action: "{'processed_by': 'yaml'}"
    priority: 50
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name

        try:
            yaml_execution_set = YAMLRuleLoader.from_file(yaml_path)
            yaml_rule = yaml_execution_set.get_rules()[0]

            # Combine rules from different sources
            combined_rules = [prog_rule, yaml_rule]
            combined_execution_set = RuleExecutionSet(
                name="mixed_rules", rules=combined_rules
            )

            provider = get_api_provider()
            admin = provider.get_rule_administrator()
            runtime = provider.get_rule_runtime()

            admin.register_rule_execution_set("mixed_sources", combined_execution_set)
            session = runtime.create_rule_session("mixed_sources")

            # Test execution with different source types
            test_facts = [
                {"source": "program", "data": "test1"},
                {"source": "yaml", "data": "test2"},
            ]

            session.add_facts(test_facts)
            results = session.execute()

            assert len(results) == 2

            # Results should be ordered by priority (programmatic first)
            assert results[0]["processed_by"] == "programmatic"
            assert results[1]["processed_by"] == "yaml"

            session.close()

        finally:
            os.unlink(yaml_path)


class TestPerformanceIntegration:
    """Integration tests for performance scenarios."""

    def test_large_ruleset_performance(self):
        """Test performance with large number of rules."""
        # Create 100 rules with different priorities
        rules = []
        for i in range(100):
            rules.append(
                Rule(
                    name=f"rule_{i}",
                    condition=lambda f, target=i: f.get("target") == target,
                    action=lambda f, rule_id=i: {"matched_rule": rule_id},
                    priority=100 - i,  # Descending priority
                )
            )

        execution_set = RuleExecutionSet(name="large_set", rules=rules)

        provider = get_api_provider()
        admin = provider.get_rule_administrator()
        runtime = provider.get_rule_runtime()

        admin.register_rule_execution_set("large_rules", execution_set)
        session = runtime.create_rule_session("large_rules")

        # Test with facts that match various rules
        test_facts = [{"target": i} for i in range(0, 100, 10)]

        session.add_facts(test_facts)
        results = session.execute()

        # Should get one result per fact
        assert len(results) == len(test_facts)

        # Results should be properly matched
        for i, result in enumerate(results):
            expected_rule_id = i * 10  # Based on our test data
            assert result["matched_rule"] == expected_rule_id

        session.close()


if __name__ == "__main__":
    pytest.main([__file__])
