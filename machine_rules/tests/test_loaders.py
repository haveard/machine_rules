"""
Test suite for rule loaders
"""

import pytest
import tempfile
import os


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

    def test_yaml_loader_validates_structure(self):
        """YAML loader should validate document structure."""
        from machine_rules.loader.yaml_loader import YAMLRuleLoader
        from machine_rules.api.exceptions import RuleValidationError

        # Missing 'name' field
        with pytest.raises(RuleValidationError, match="name|required"):
            YAMLRuleLoader.from_dict({'rules': []})

        # Missing 'rules' field
        with pytest.raises(RuleValidationError, match="rules|required"):
            YAMLRuleLoader.from_dict({'name': 'test'})

    def test_yaml_loader_validates_rule_fields(self):
        """Each rule should have required fields."""
        from machine_rules.loader.yaml_loader import YAMLRuleLoader
        from machine_rules.api.exceptions import RuleValidationError

        # Rule missing 'name'
        with pytest.raises(RuleValidationError, match="name|required"):
            YAMLRuleLoader.from_dict({
                'name': 'test',
                'rules': [{'condition': 'True', 'action': '{}'}]
            })

        # Rule missing 'condition'
        with pytest.raises(RuleValidationError, match="condition|required"):
            YAMLRuleLoader.from_dict({
                'name': 'test',
                'rules': [{'name': 'rule1', 'action': '{}'}]
            })

        # Rule missing 'action'
        with pytest.raises(RuleValidationError, match="action|required"):
            YAMLRuleLoader.from_dict({
                'name': 'test',
                'rules': [{'name': 'rule1', 'condition': 'True'}]
            })

    def test_yaml_loader_validates_expression_safety(self):
        """YAML loader should detect unsafe expressions during validation."""
        from machine_rules.loader.yaml_loader import YAMLRuleLoader
        from machine_rules.api.exceptions import RuleValidationError

        # Attempt to use __import__
        with pytest.raises(RuleValidationError, match="unsafe|security|forbidden"):
            YAMLRuleLoader.from_dict({
                'name': 'test',
                'rules': [{
                    'name': 'rule1',
                    'condition': '__import__("os").system("ls")',
                    'action': '{}'
                }]
            })

        # Attempt to use eval
        with pytest.raises(RuleValidationError, match="unsafe|security|forbidden"):
            YAMLRuleLoader.from_dict({
                'name': 'test',
                'rules': [{
                    'name': 'rule1',
                    'condition': 'True',
                    'action': 'eval("print(1)")'
                }]
            })

    def test_yaml_loader_validates_types(self):
        """YAML loader should validate field types."""
        from machine_rules.loader.yaml_loader import YAMLRuleLoader
        from machine_rules.api.exceptions import RuleValidationError

        # 'rules' should be a list
        with pytest.raises(RuleValidationError, match="rules|list|array"):
            YAMLRuleLoader.from_dict({
                'name': 'test',
                'rules': 'not a list'
            })

        # 'priority' should be numeric
        with pytest.raises(RuleValidationError, match="priority|number|integer"):
            YAMLRuleLoader.from_dict({
                'name': 'test',
                'rules': [{
                    'name': 'rule1',
                    'condition': 'True',
                    'action': '{}',
                    'priority': 'high'  # Should be int
                }]
            })


# DMN loader tests removed - DMN loader deprecated and removed due to security vulnerabilities


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
