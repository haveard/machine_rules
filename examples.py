#!/usr/bin/env python3
"""
Example usage of Machine Rules Engine

This script demonstrates how to use the JSR-94 compatible rules engine
for Python with different rule loaders and execution patterns.
"""

import tempfile
import os
from machine_rules.api.registry import RuleServiceProviderManager
from machine_rules.api.execution_set import Rule, RuleExecutionSet
from machine_rules.loader.yaml_loader import YAMLRuleLoader
from machine_rules.loader.dmn_loader import DMNRuleLoader
import pandas as pd


def example_programmatic_rules():
    """Example of creating rules programmatically."""
    print("=== Programmatic Rules Example ===")

    # Define rule functions
    def high_income_condition(fact):
        return fact.get('income', 0) > 100000

    def high_income_action(fact):
        return {
            'category': 'high_income',
            'discount': 0.15,
            'message': f"VIP customer with income ${fact.get('income', 0):,}"
        }

    def standard_income_condition(fact):
        return fact.get('income', 0) <= 100000

    def standard_income_action(fact):
        income = fact.get('income', 0)
        return {
            'category': 'standard',
            'discount': 0.05,
            'message': f"Standard customer with income ${income:,}"
        }

    # Create rules
    high_income_rule = Rule(
        name="high_income_rule",
        condition=high_income_condition,
        action=high_income_action,
        priority=10
    )

    standard_income_rule = Rule(
        name="standard_income_rule",
        condition=standard_income_condition,
        action=standard_income_action,
        priority=5
    )

    # Create rule execution set
    execution_set = RuleExecutionSet(
        name="income_classification_rules",
        rules=[high_income_rule, standard_income_rule],
        properties={'description': 'Customer income classification rules'}
    )

    # Get rule service provider
    provider = RuleServiceProviderManager.get("api")
    if provider is None:
        raise RuntimeError("No provider registered for 'api'")
    admin = provider.get_rule_administrator()
    runtime = provider.get_rule_runtime()

    # Register the rule set
    admin.register_rule_execution_set("income_rules", execution_set)

    # Execute rules
    session = runtime.create_rule_session("income_rules", stateless=True)

    test_facts = [
        {'income': 150000, 'name': 'John Doe'},
        {'income': 75000, 'name': 'Jane Smith'},
        {'income': 200000, 'name': 'Bob Johnson'},
        {'income': 45000, 'name': 'Alice Brown'}
    ]

    session.add_facts(test_facts)
    results = session.execute()

    print(f"Processed {len(test_facts)} facts, got {len(results)} results:")
    for i, result in enumerate(results):
        print(f"  {i+1}. {result}")

    session.close()


def example_yaml_rules():
    """Example of loading rules from YAML."""
    print("\n=== YAML Rules Example ===")

    yaml_content = """
name: "customer_segmentation"
description: "Customer segmentation rules based on various criteria"
rules:
  - name: "vip_customer"
    condition: >
      fact.get('income', 0) > 150000 and
      fact.get('loyalty_years', 0) > 5
    action: >
      {'segment': 'VIP', 'priority': 'highest',
       'perks': ['free_shipping', 'personal_advisor']}
    priority: 20

  - name: "premium_customer"
    condition: >
      fact.get('income', 0) > 100000 or
      fact.get('loyalty_years', 0) > 3
    action: >
      {'segment': 'Premium', 'priority': 'high',
       'perks': ['free_shipping']}
    priority: 15

  - name: "standard_customer"
    condition: "True"  # Default rule
    action: "{'segment': 'Standard', 'priority': 'normal', 'perks': []}"
    priority: 1
"""

    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.yaml', delete=False
    ) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        # Load rules from YAML
        execution_set = YAMLRuleLoader.from_file(temp_path)

        # Register and execute
        provider = RuleServiceProviderManager.get("api")
        if provider is None:
            raise RuntimeError("No provider registered for 'api'")
        admin = provider.get_rule_administrator()
        runtime = provider.get_rule_runtime()

        admin.register_rule_execution_set(
            "customer_segmentation", execution_set
        )

        session = runtime.create_rule_session("customer_segmentation")

        test_customers = [
            {'income': 180000, 'loyalty_years': 7, 'name': 'VIP Customer'},
            {
                'income': 120000, 'loyalty_years': 2,
                'name': 'Premium by Income'
            },
            {
                'income': 80000, 'loyalty_years': 4,
                'name': 'Premium by Loyalty'
            },
            {'income': 60000, 'loyalty_years': 1, 'name': 'Standard Customer'}
        ]

        session.add_facts(test_customers)
        results = session.execute()

        print("Customer segmentation results:")
        # Since rules are prioritized and only one rule fires per fact,
        # we need to match results to customers correctly
        result_index = 0
        for customer in test_customers:
            # Check if this customer would match any rule and get the result
            for rule in execution_set.get_rules():
                if rule.condition(customer):
                    if result_index < len(results):
                        print(f"  {customer['name']}: {results[result_index]}")
                        result_index += 1
                    break
            else:
                print(f"  {customer['name']}: No rule matched")

        session.close()

    finally:
        os.unlink(temp_path)


def example_dmn_rules():
    """Example of loading rules from Excel (DMN-style)."""
    print("\n=== DMN Excel Rules Example ===")

    # Create test Excel file
    data = {
        'condition': ['>120000', '<=120000'],
        'action': ['"luxury"', '"economy"']
    }

    # Note: For this example, we'll simulate the Excel loading
    # In practice, you would create an actual Excel file
    df = pd.DataFrame(data)

    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        df.to_excel(f.name, index=False)
        temp_path = f.name

    try:
        # Load rules from Excel
        execution_set = DMNRuleLoader.from_excel(temp_path)

        # Register and execute
        provider = RuleServiceProviderManager.get("api")
        if provider is None:
            raise RuntimeError("No provider registered for 'api'")
        admin = provider.get_rule_administrator()
        runtime = provider.get_rule_runtime()

        admin.register_rule_execution_set("lifestyle_rules", execution_set)

        session = runtime.create_rule_session("lifestyle_rules")

        test_income_data = [
            {'income': 150000},
            {'income': 95000},
            {'income': 65000}
        ]

        session.add_facts(test_income_data)
        results = session.execute()

        print("Lifestyle classification results:")
        for i, result in enumerate(results):
            income = test_income_data[i]['income']
            print(f"  Income ${income:,}: {result}")

        session.close()

    finally:
        os.unlink(temp_path)


def main():
    """Run all examples."""
    print("Machine Rules Engine - JSR-94 Compatible Examples")
    print("=" * 60)

    # Initialize the rules engine (this happens automatically on import)
    print("Rules engine initialized with providers:")
    for uri in RuleServiceProviderManager.get_registered_uris():
        print(f"  - {uri}")

    try:
        example_programmatic_rules()
        example_yaml_rules()
        example_dmn_rules()

        print("\n=== All Examples Completed Successfully ===")

    except Exception as e:
        print(f"\nError running examples: {e}")
        raise


if __name__ == "__main__":
    main()
