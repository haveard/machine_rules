from typing import Dict, Any, List, Optional
from ..api.administrator import RuleAdministrator
from ..api.runtime import RuleRuntime
from ..api.session import RuleSession
from ..api.execution_set import RuleExecutionSet
from ..api.registry import RuleServiceProvider


class MachineRuleSession(RuleSession):
    """
    Concrete implementation of RuleSession using the Machine rules engine.
    """

    def __init__(self, execution_set: RuleExecutionSet):
        self.execution_set = execution_set
        self.facts = []
        self.results = []
        self._closed = False

    def add_facts(self, facts: List[Any]):
        """Add facts to the session."""
        if self._closed:
            raise RuntimeError("Session is closed")
        self.facts.extend(facts)

    def execute(self) -> List[Any]:
        """Execute rules and return results."""
        if self._closed:
            raise RuntimeError("Session is closed")

        self.results = []
        for fact in self.facts:
            for rule in self.execution_set.get_rules():
                try:
                    if rule.condition(fact):
                        result = rule.action(fact)
                        if result is not None:
                            self.results.append(result)
                except Exception as e:
                    # Log error and continue with next rule
                    print(f"Error executing rule {rule.name}: {e}")

        return self.results.copy()

    def close(self):
        """Close the session and release resources."""
        self.facts.clear()
        self.results.clear()
        self._closed = True

    def reset(self):
        """Reset the session state."""
        if self._closed:
            raise RuntimeError("Session is closed")
        self.facts.clear()
        self.results.clear()


class MachineRuleAdministrator(RuleAdministrator):
    """
    Concrete implementation of RuleAdministrator for the Machine rules engine.
    """

    def __init__(self):
        self.registrations = {}

    def register_rule_execution_set(
        self,
        name: str,
        execution_set: RuleExecutionSet,
        properties: Optional[Dict[str, Any]] = None
    ):
        """Register a RuleExecutionSet with the administrator."""
        if properties is None:
            properties = {}
        self.registrations[name] = execution_set

    def deregister_rule_execution_set(
        self,
        name: str,
        properties: Optional[Dict[str, Any]] = None
    ):
        """Remove a RuleExecutionSet registration."""
        if properties is None:
            properties = {}
        self.registrations.pop(name, None)

    def get_registrations(self) -> Dict[str, RuleExecutionSet]:
        """Get all registered RuleExecutionSets."""
        return self.registrations.copy()


class MachineRuleRuntime(RuleRuntime):
    """
    Concrete implementation of RuleRuntime for the Machine rules engine.
    """

    def __init__(self, administrator: MachineRuleAdministrator):
        self.administrator = administrator

    def create_rule_session(
        self,
        uri: str,
        properties: Optional[Dict[str, Any]] = None,
        stateless: bool = False
    ) -> RuleSession:
        """Create a rule session for executing rules."""
        if properties is None:
            properties = {}
        execution_set = self.administrator.registrations.get(uri)
        if not execution_set:
            msg = f"No rule execution set registered for URI: {uri}"
            raise ValueError(msg)
        return MachineRuleSession(execution_set)

    def get_registrations(self) -> List[str]:
        """Get URIs of all registered rule execution sets."""
        return list(self.administrator.registrations.keys())


class MachineRuleServiceProvider(RuleServiceProvider):
    """
    Concrete implementation of RuleServiceProvider for Machine rules engine.
    """

    def __init__(self):
        self.administrator = MachineRuleAdministrator()
        self.runtime = MachineRuleRuntime(self.administrator)

    def get_rule_administrator(self) -> RuleAdministrator:
        """Get the rule administrator for this provider."""
        return self.administrator

    def get_rule_runtime(self) -> RuleRuntime:
        """Get the rule runtime for this provider."""
        return self.runtime
