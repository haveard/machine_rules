#!/usr/bin/env python3
"""
Example usage of Machine Rules Engine

This script demonstrates how to use the JSR-94 compatible rules engine
for Python with different rule loaders and execution patterns.

Examples included:
1. Programmatic rules - Create rules using Python functions
2. YAML rules - Load rules from YAML configuration
3. Complex business logic - Multi-criteria decision making
4. Stateless vs stateful sessions

Run: python examples.py
"""

import tempfile
import os
from typing import Dict, Any, List
from machine_rules.api.registry import RuleServiceProviderManager
from machine_rules.api.execution_set import Rule, RuleExecutionSet
from machine_rules.loader.yaml_loader import YAMLRuleLoader


def example_programmatic_rules():
    """Example of creating rules programmatically."""
    print("\n=== Programmatic Rules Example ===")
    print("Demonstrating: Creating rules with Python functions\n")

    # Define rule functions with clear business logic
    def high_income_condition(fact: Dict[str, Any]) -> bool:
        """Check if customer qualifies for VIP status."""
        return fact.get('income', 0) > 100000

    def high_income_action(fact: Dict[str, Any]) -> Dict[str, Any]:
        """Apply VIP customer benefits."""
        return {
            'category': 'high_income',
            'discount': 0.15,
            'credit_limit': 50000,
            'message': f"VIP customer: {fact.get('name')} - Income ${fact.get('income', 0):,}"
        }

    def standard_income_condition(fact: Dict[str, Any]) -> bool:
        """Check if customer is in standard tier."""
        return fact.get('income', 0) <= 100000

    def standard_income_action(fact: Dict[str, Any]) -> Dict[str, Any]:
        """Apply standard customer benefits."""
        income = fact.get('income', 0)
        return {
            'category': 'standard',
            'discount': 0.05,
            'credit_limit': 10000,
            'message': f"Standard customer: {fact.get('name')} - Income ${income:,}"
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

    # Execute rules with stateless session
    session = runtime.create_rule_session("income_rules", stateless=True)

    test_facts: List[Dict[str, Any]] = [
        {'income': 150000, 'name': 'John Doe'},
        {'income': 75000, 'name': 'Jane Smith'},
        {'income': 200000, 'name': 'Bob Johnson'},
        {'income': 45000, 'name': 'Alice Brown'}
    ]

    session.add_facts(test_facts)
    results = session.execute()

    print(f"📊 Processed {len(test_facts)} customers:")
    print("-" * 70)
    for i, result in enumerate(results, 1):
        category = result.get('category', 'unknown')
        discount = result.get('discount', 0) * 100
        credit = result.get('credit_limit', 0)
        msg = result.get('message', '')
        print(f"{i}. {msg}")
        print(f"   Category: {category.upper()} | Discount: {discount}% | Credit Limit: ${credit:,}")
    print("-" * 70)

    session.close()


def example_yaml_rules():
    """Example of loading rules from YAML."""
    print("\n=== YAML Rules Example ===")
    print("Demonstrating: Loading rules from YAML configuration\n")

    yaml_content = """
name: "customer_segmentation"
description: "Customer segmentation rules based on various criteria"
rules:
  - name: "vip_customer"
    condition: >
      fact.get('income', 0) > 150000 and
      fact.get('loyalty_years', 0) > 5
    action: >
      {
        'segment': 'VIP',
        'priority': 'highest',
        'perks': ['free_shipping', 'personal_advisor', 'early_access'],
        'retention_bonus': 1000
      }
    priority: 20

  - name: "premium_customer"
    condition: >
      fact.get('income', 0) > 100000 or
      fact.get('loyalty_years', 0) > 3
    action: >
      {
        'segment': 'Premium',
        'priority': 'high',
        'perks': ['free_shipping', 'priority_support'],
        'retention_bonus': 250
      }
    priority: 15

  - name: "standard_customer"
    condition: "True"  # Default rule
    action: >
      {
        'segment': 'Standard',
        'priority': 'normal',
        'perks': [],
        'retention_bonus': 0
      }
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

        print("📈 Customer Segmentation Results:")
        print("-" * 70)
        # Since rules are prioritized and only one rule fires per fact,
        # we need to match results to customers correctly
        result_index = 0
        for customer in test_customers:
            # Check if this customer would match any rule and get the result
            for rule in execution_set.get_rules():
                if rule.condition(customer):
                    if result_index < len(results):
                        result = results[result_index]
                        segment = result.get('segment', 'Unknown')
                        perks = ', '.join(result.get('perks', []))
                        bonus = result.get('retention_bonus', 0)
                        print(f"👤 {customer['name']:20} | {segment:10} | Bonus: ${bonus:4}")
                        if perks:
                            print(f"   Perks: {perks}")
                        result_index += 1
                    break
            else:
                print(f"👤 {customer['name']:20} | No rule matched")
        print("-" * 70)

        session.close()

    finally:
        os.unlink(temp_path)


def example_complex_business_logic():
    """Example of complex multi-criteria business logic."""
    print("\n=== Complex Business Logic Example ===")
    print("Demonstrating: Multi-criteria loan approval decision\n")

    # Define complex loan approval rules
    def excellent_credit_rule(fact: Dict[str, Any]) -> bool:
        """Excellent credit score with stable income."""
        return (
            fact.get('credit_score', 0) >= 750 and
            fact.get('income', 0) >= 50000 and
            fact.get('debt_to_income', 1.0) <= 0.3
        )

    def excellent_credit_action(fact: Dict[str, Any]) -> Dict[str, Any]:
        """Approve loan with best terms."""
        return {
            'approved': True,
            'rate': 3.5,
            'max_amount': min(fact.get('income', 0) * 5, 500000),
            'reason': 'Excellent credit and financial profile',
            'decision': 'APPROVED'
        }

    def good_credit_rule(fact: Dict[str, Any]) -> bool:
        """Good credit with acceptable metrics."""
        return (
            fact.get('credit_score', 0) >= 650 and
            fact.get('income', 0) >= 40000 and
            fact.get('debt_to_income', 1.0) <= 0.43
        )

    def good_credit_action(fact: Dict[str, Any]) -> Dict[str, Any]:
        """Approve loan with standard terms."""
        return {
            'approved': True,
            'rate': 5.5,
            'max_amount': min(fact.get('income', 0) * 3, 300000),
            'reason': 'Good credit and acceptable debt ratio',
            'decision': 'APPROVED'
        }

    def manual_review_rule(fact: Dict[str, Any]) -> bool:
        """Borderline case requiring manual review."""
        return (
            fact.get('credit_score', 0) >= 600 and
            fact.get('income', 0) >= 30000
        )

    def manual_review_action(fact: Dict[str, Any]) -> Dict[str, Any]:
        """Requires manual underwriting review."""
        return {
            'approved': False,
            'rate': 0.0,
            'max_amount': 0,
            'reason': 'Requires manual underwriting review',
            'decision': 'MANUAL_REVIEW'
        }

    def decline_rule(fact: Dict[str, Any]) -> bool:
        """Does not meet minimum requirements."""
        return True  # Catch-all rule

    def decline_action(fact: Dict[str, Any]) -> Dict[str, Any]:
        """Decline loan application."""
        return {
            'approved': False,
            'rate': 0.0,
            'max_amount': 0,
            'reason': 'Does not meet minimum credit or income requirements',
            'decision': 'DECLINED'
        }

    # Create rule execution set
    rules = [
        Rule("excellent_credit", excellent_credit_rule, excellent_credit_action, priority=100),
        Rule("good_credit", good_credit_rule, good_credit_action, priority=75),
        Rule("manual_review", manual_review_rule, manual_review_action, priority=50),
        Rule("decline", decline_rule, decline_action, priority=1)
    ]

    execution_set = RuleExecutionSet(
        name="loan_approval_rules",
        rules=rules,
        properties={'description': 'Automated loan approval decision engine'}
    )

    # Register and execute
    provider = RuleServiceProviderManager.get("api")
    if provider is None:
        raise RuntimeError("No provider registered for 'api'")
    admin = provider.get_rule_administrator()
    runtime = provider.get_rule_runtime()

    admin.register_rule_execution_set("loan_approval", execution_set)
    session = runtime.create_rule_session("loan_approval")

    # Test loan applications
    applications: List[Dict[str, Any]] = [
        {
            'name': 'Alice Premium',
            'credit_score': 780,
            'income': 120000,
            'debt_to_income': 0.25
        },
        {
            'name': 'Bob Standard',
            'credit_score': 680,
            'income': 65000,
            'debt_to_income': 0.38
        },
        {
            'name': 'Carol Borderline',
            'credit_score': 620,
            'income': 45000,
            'debt_to_income': 0.50
        },
        {
            'name': 'David Declined',
            'credit_score': 550,
            'income': 25000,
            'debt_to_income': 0.60
        }
    ]

    session.add_facts(applications)
    results = session.execute()

    print("💳 Loan Application Decisions:")
    print("-" * 80)
    for i, (app, result) in enumerate(zip(applications, results), 1):
        decision = result.get('decision', 'UNKNOWN')
        decision_icon = '✅' if result.get('approved') else '❌' if decision == 'DECLINED' else '⏳'
        
        print(f"{decision_icon} {app['name']:20} | Score: {app['credit_score']:3} | "
              f"Income: ${app['income']:,}")
        print(f"   Decision: {decision:15} | Rate: {result.get('rate'):.1f}% | "
              f"Max: ${result.get('max_amount'):,}")
        print(f"   Reason: {result.get('reason')}")
        if i < len(results):
            print()
    print("-" * 80)

    session.close()


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("  Machine Rules Engine - JSR-94 Compatible Examples")
    print("  Demonstrating rule-based decision making in Python")
    print("=" * 80)

    # Initialize the rules engine (this happens automatically on import)
    print("\n🔧 Rules engine initialized with providers:")
    for uri in RuleServiceProviderManager.get_registered_uris():
        print(f"   • {uri}")

    try:
        example_programmatic_rules()
        example_yaml_rules()
        example_complex_business_logic()

        print("\n" + "=" * 80)
        print("✅ All Examples Completed Successfully")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        raise


if __name__ == "__main__":
    main()
