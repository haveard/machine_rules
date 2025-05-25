import pandas as pd
from machine_rules.api.execution_set import RuleExecutionSet, Rule


class DMNRuleLoader:
    @staticmethod
    def from_excel(filepath: str) -> RuleExecutionSet:
        df = pd.read_excel(filepath)
        rules = []

        for idx, row in df.iterrows():
            cond_expr = row.iloc[0]  # e.g., '>100000'
            action_expr = row.iloc[1]  # e.g., '"High Income"'

            def make_condition(expr):
                condition_code = compile(
                    f"fact.get('income', 0) {expr}", '<string>', 'eval'
                )
                return lambda fact: eval(condition_code, {}, {'fact': fact})

            def make_action(expr):
                action_code = compile(
                    f"{{'result': {expr}}}", '<string>', 'eval'
                )
                return lambda fact: eval(action_code, {}, {'fact': fact})

            rule = Rule(
                name=f"rule_{idx}",
                condition=make_condition(cond_expr),
                action=make_action(action_expr),
                priority=0
            )
            rules.append(rule)

        return RuleExecutionSet(name="dmn_rules", rules=rules)
