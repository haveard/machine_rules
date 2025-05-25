import yaml
from typing import Dict, Any
from machine_rules.api.execution_set import RuleExecutionSet, Rule


class YAMLRuleLoader:
    """
    Loader for YAML-based rule definitions.

    Expected YAML format:
    ```yaml
    name: "example_rules"
    description: "Example rule set"
    rules:
      - name: "high_income_rule"
        condition: "fact.get('income', 0) > 100000"
        action: "{'category': 'high_income', 'discount': 0.1}"
        priority: 10
      - name: "low_income_rule"
        condition: "fact.get('income', 0) <= 100000"
        action: "{'category': 'standard', 'discount': 0.0}"
        priority: 5
    ```
    """

    @staticmethod
    def from_file(filepath: str) -> RuleExecutionSet:
        """Load rules from a YAML file."""
        with open(filepath, 'r') as file:
            data = yaml.safe_load(file)

        return YAMLRuleLoader.from_dict(data)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> RuleExecutionSet:
        """Load rules from a dictionary structure."""
        name = data.get('name', 'yaml_rules')
        description = data.get('description', '')
        rule_definitions = data.get('rules', [])

        rules = []
        for rule_def in rule_definitions:
            rule = YAMLRuleLoader._create_rule_from_definition(rule_def)
            rules.append(rule)

        properties = {
            'description': description,
            'source': 'yaml'
        }

        return RuleExecutionSet(name=name, rules=rules, properties=properties)

    @staticmethod
    def _create_rule_from_definition(rule_def: Dict[str, Any]) -> Rule:
        """Create a Rule object from a rule definition dictionary."""
        name = rule_def.get('name', 'unnamed_rule')
        condition_expr = rule_def.get('condition', 'True')
        action_expr = rule_def.get('action', 'None')
        priority = rule_def.get('priority', 0)

        # Compile condition and action expressions
        condition_code = compile(
            condition_expr, f'<rule:{name}:condition>', 'eval'
        )
        action_code = compile(action_expr, f'<rule:{name}:action>', 'eval')

        def condition_func(fact):
            try:
                return eval(
                    condition_code, {"__builtins__": {}}, {'fact': fact}
                )
            except Exception as e:
                print(f"Error evaluating condition for rule {name}: {e}")
                return False

        def action_func(fact):
            try:
                return eval(action_code, {"__builtins__": {}}, {'fact': fact})
            except Exception as e:
                print(f"Error evaluating action for rule {name}: {e}")
                return None

        return Rule(
            name=name,
            condition=condition_func,
            action=action_func,
            priority=priority
        )
