import yaml  # type: ignore[import-untyped]
import logging
from typing import Dict, Any
from pydantic import ValidationError
from machine_rules.api.execution_set import RuleExecutionSet, Rule
from machine_rules.api.exceptions import RuleValidationError
from machine_rules.security import safe_eval, SecurityError
from machine_rules.schemas.rule_schema import RuleSetDefinition

logger = logging.getLogger(__name__)


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
        """Load rules from a dictionary structure.
        
        Validates the input structure using Pydantic schemas before creating rules.
        
        Raises:
            RuleValidationError: If the input structure or expressions are invalid.
        """
        try:
            # Validate the input structure using Pydantic schema
            validated_data = RuleSetDefinition.model_validate(data)
        except ValidationError as e:
            # Convert Pydantic validation error to RuleValidationError
            error_messages = []
            for error in e.errors():
                loc = ' -> '.join(str(location) for location in error['loc'])
                error_messages.append(f"{loc}: {error['msg']}")
            raise RuleValidationError(
                f"Invalid rule set structure: {'; '.join(error_messages)}"
            )
        
        # Extract validated data
        name = validated_data.name
        description = validated_data.description
        rule_definitions = validated_data.rules

        rules = []
        for rule_def in rule_definitions:
            # Convert Pydantic model to dict for _create_rule_from_definition
            rule_dict = rule_def.model_dump()
            rule = YAMLRuleLoader._create_rule_from_definition(rule_dict)
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

        # Use safe evaluator instead of eval()
        def condition_func(fact):
            try:
                return safe_eval(condition_expr, {'fact': fact})
            except SecurityError as e:
                logger.error(f"Security error in condition for rule {name}: {e}")
                return False
            except Exception as e:
                logger.error(f"Error evaluating condition for rule {name}: {e}")
                return False

        def action_func(fact):
            try:
                return safe_eval(action_expr, {'fact': fact})
            except SecurityError as e:
                logger.error(f"Security error in action for rule {name}: {e}")
                return None
            except Exception as e:
                logger.error(f"Error evaluating action for rule {name}: {e}")
                return None

        return Rule(
            name=name,
            condition=condition_func,
            action=action_func,
            priority=priority
        )
