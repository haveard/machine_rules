"""
Test suite for rule loaders
"""

import pytest
import tempfile
import os
import pandas as pd


class TestYAMLRuleLoader:
    """Test the YAML rule loader."""

    def test_yaml_loader_from_dict(self):
        from machine_rules.loader.yaml_loader import YAMLRuleLoader

        data = {
            'name': 'test_rules',
            'description': 'Test rule set',
            'rules': [
                {
                    'name': 'high_income_rule',
                    'condition': "fact.get('income', 0) > 100000",
                    'action': "{'category': 'high_income'}",
                    'priority': 10
                },
                {
                    'name': 'low_income_rule',
                    'condition': "fact.get('income', 0) <= 100000",
                    'action': "{'category': 'standard'}",
                    'priority': 5
                }
            ]
        }

        execution_set = YAMLRuleLoader.from_dict(data)

        assert execution_set.get_name() == 'test_rules'
        assert execution_set.get_description() == 'Test rule set'

        rules = execution_set.get_rules()
        assert len(rules) == 2

        # Check rule ordering by priority
        assert rules[0].name == 'high_income_rule'
        assert rules[1].name == 'low_income_rule'

        # Test rule execution
        high_income_fact = {'income': 150000}
        low_income_fact = {'income': 50000}

        assert rules[0].condition(high_income_fact) is True
        assert rules[0].condition(low_income_fact) is False
        assert rules[1].condition(low_income_fact) is True

        assert rules[0].action(high_income_fact) == {'category': 'high_income'}
        assert rules[1].action(low_income_fact) == {'category': 'standard'}

    def test_yaml_loader_from_file(self):
        from machine_rules.loader.yaml_loader import YAMLRuleLoader

        yaml_content = """
name: "file_test_rules"
description: "Rules loaded from file"
rules:
  - name: "test_rule"
    condition: "fact.get('value', 0) > 10"
    action: "{'result': 'pass'}"
    priority: 1
"""

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            execution_set = YAMLRuleLoader.from_file(temp_path)

            assert execution_set.get_name() == 'file_test_rules'
            assert len(execution_set.get_rules()) == 1

            rule = execution_set.get_rules()[0]
            assert rule.name == 'test_rule'
            assert rule.condition({'value': 15}) is True
            assert rule.action({'value': 15}) == {'result': 'pass'}

        finally:
            os.unlink(temp_path)


class TestDMNRuleLoader:
    """Test the DMN rule loader."""

    def test_dmn_loader_from_excel(self):
        from machine_rules.loader.dmn_loader import DMNRuleLoader

        # Create a test Excel file
        data = {
            'condition': ['>100000', '<=100000'],
            'action': ['"high_income"', '"standard"']
        }
        df = pd.DataFrame(data)

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            df.to_excel(f.name, index=False)
            temp_path = f.name

        try:
            execution_set = DMNRuleLoader.from_excel(temp_path)

            assert execution_set.get_name() == 'dmn_rules'

            rules = execution_set.get_rules()
            assert len(rules) == 2

            # Test rule execution
            high_income_fact = {'income': 150000}
            low_income_fact = {'income': 50000}

            # Test first rule (>100000)
            rule_0 = rules[0]
            assert rule_0.condition(high_income_fact) is True
            assert rule_0.condition(low_income_fact) is False
            assert rule_0.action(high_income_fact) == {'result': 'high_income'}

            # Test second rule (<=100000)
            rule_1 = rules[1]
            assert rule_1.condition(low_income_fact) is True
            assert rule_1.condition(high_income_fact) is False
            assert rule_1.action(low_income_fact) == {'result': 'standard'}

        finally:
            os.unlink(temp_path)


class TestIntegrationWithLoaders:
    """Integration tests using loaders with the full rule engine."""

    def test_yaml_integration(self):
        from machine_rules.loader.yaml_loader import YAMLRuleLoader
        from machine_rules.adapters.machine_adapter import (
            MachineRuleServiceProvider
        )

        # Create rules using YAML loader
        data = {
            'name': 'integration_test_rules',
            'rules': [
                {
                    'name': 'age_check',
                    'condition': "fact.get('age', 0) >= 18",
                    'action': "{'status': 'adult'}",
                    'priority': 1
                }
            ]
        }

        execution_set = YAMLRuleLoader.from_dict(data)

        # Register with rule engine
        provider = MachineRuleServiceProvider()
        admin = provider.get_rule_administrator()
        runtime = provider.get_rule_runtime()

        admin.register_rule_execution_set("age_rules", execution_set)

        # Execute rules
        session = runtime.create_rule_session("age_rules")
        session.add_facts([{'age': 25}, {'age': 16}])

        results = session.execute()

        assert len(results) == 1
        assert results[0] == {'status': 'adult'}

        session.close()


if __name__ == "__main__":
    pytest.main([__file__])
