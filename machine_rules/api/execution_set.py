from typing import List, Dict, Any, Callable, Optional


class Rule:
    """
    Represents a single rule with condition and action.
    """

    def __init__(
        self, name: str, condition: Callable, action: Callable, priority: int = 0
    ):
        self.name = name
        self.condition = condition
        self.action = action
        self.priority = priority

    def __str__(self):
        return f"Rule(name={self.name}, priority={self.priority})"

    def __repr__(self):
        return self.__str__()


class RuleExecutionSet:
    """
    A collection of rules that can be executed together.
    Follows JSR-94 specification for RuleExecutionSet.
    """

    def __init__(
        self, name: str, rules: List[Rule], properties: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        self.properties = properties or {}

    def get_rules(self) -> List[Rule]:
        """Get all rules in this execution set."""
        return self.rules

    def get_name(self) -> str:
        """Get the name of this execution set."""
        return self.name

    def get_description(self) -> str:
        """Get the description of this execution set."""
        return self.properties.get("description", "")

    def get_properties(self) -> Dict[str, Any]:
        """Get all properties of this execution set."""
        return self.properties.copy()

    def __str__(self):
        return f"RuleExecutionSet(name={self.name}, rules={len(self.rules)})"

    def __repr__(self):
        return self.__str__()
