"""
Test suite for FastAPI integration
"""

import pytest
from fastapi.testclient import TestClient


class TestFastAPIIntegration:
    """Test the FastAPI integration."""

    def test_execute_endpoint_no_rules(self):
        # Ensure initialization happens
        import machine_rules  # noqa: F401

        from machine_rules.__main__ import app

        client = TestClient(app)

        # Test with non-existent ruleset
        response = client.post(
            "/execute",
            json={
                "facts": [{"income": 50000}],
                "ruleset_uri": "nonexistent"
            }
        )

        # Should get a 400 error due to ValueError being raised
        assert response.status_code == 400

    def test_execute_endpoint_with_rules(self):
        # Ensure initialization happens
        import machine_rules  # noqa: F401

        from machine_rules.__main__ import app
        from machine_rules.api.registry import (
            RuleServiceProviderManager
        )
        from machine_rules.api.execution_set import (
            Rule, RuleExecutionSet
        )

        client = TestClient(app)

        # Set up a test rule
        def condition(fact):
            return fact.get('income', 0) > 50000

        def action(fact):
            return {'category': 'high_income'}

        rule = Rule(name="income_test", condition=condition, action=action)
        execution_set = RuleExecutionSet(name="test_rules", rules=[rule])

        # Register the rule set
        provider = RuleServiceProviderManager.get("api")
        assert provider is not None, "RuleServiceProviderManager.get('api') returned None"
        admin = provider.get_rule_administrator()
        admin.register_rule_execution_set("test_income_rules", execution_set)

        # Test execution
        response = client.post(
            "/execute",
            json={
                "facts": [{"income": 75000}, {"income": 25000}],
                "ruleset_uri": "test_income_rules"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        # Only one fact (income: 75000) should match the condition > 50000
        assert len(data["results"]) == 1
        assert data["results"][0] == {"category": "high_income"}


if __name__ == "__main__":
    pytest.main([__file__])
