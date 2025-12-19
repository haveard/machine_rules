import logging
import threading
from typing import Dict, Any, List, Optional
from ..api.administrator import RuleAdministrator
from ..api.runtime import RuleRuntime
from ..api.session import RuleSession
from ..api.execution_set import RuleExecutionSet
from ..api.registry import RuleServiceProvider
from ..api.exceptions import SessionError, RuleValidationError

logger = logging.getLogger(__name__)


class MachineRuleSession(RuleSession):
    """
    Concrete implementation of RuleSession using the Machine rules engine.
    
    Args:
        execution_set: The rule execution set to use
        stateless: If True, facts are cleared after each execute() call
    """

    def __init__(self, execution_set: RuleExecutionSet, stateless: bool = False):
        self.execution_set = execution_set
        self.facts: List[Any] = []
        self.results: List[Any] = []
        self._closed = False
        self.stateless = stateless

    def add_facts(self, facts: List[Any]):
        """Add facts to the session."""
        if self._closed:
            raise SessionError("Session is closed")
        if not isinstance(facts, list):
            raise RuleValidationError("Facts must be a list")
        self.facts.extend(facts)

    def execute(self) -> List[Any]:
        """Execute rules and return results.
        
        Execution strategy can be configured via execution_set properties:
        - 'ALL_MATCHES' (default): Execute all matching rules for each fact
        - 'FIRST_MATCH': Stop after first matching rule per fact (short-circuit)
        
        If stateless=True, facts are automatically cleared after execution.
        """
        if self._closed:
            raise SessionError("Session is closed")

        # Get execution strategy from properties (default to ALL_MATCHES)
        strategy = self.execution_set.get_properties().get('strategy', 'ALL_MATCHES')

        self.results = []
        for fact in self.facts:
            for rule in self.execution_set.get_rules():
                try:
                    if rule.condition(fact):
                        result = rule.action(fact)
                        if result is not None:
                            self.results.append(result)
                        
                        # If FIRST_MATCH strategy, stop after first match per fact
                        if strategy == 'FIRST_MATCH':
                            break
                except Exception as e:
                    # Log error and continue with next rule
                    logger.error(f"Error executing rule {rule.name}: {e}", exc_info=True)

        # Clear facts if stateless mode
        if self.stateless:
            self.facts.clear()

        return self.results.copy()

    def close(self):
        """Close the session and release resources."""
        self.facts.clear()
        self.results.clear()
        self._closed = True

    def reset(self):
        """Reset the session state."""
        if self._closed:
            raise SessionError("Session is closed")
        self.facts.clear()
        self.results.clear()


class MachineRuleAdministrator(RuleAdministrator):
    """Thread-safe implementation of RuleAdministrator for the Machine rules engine.
    
    This class uses a reentrant lock to ensure thread-safe operations
    when registering, retrieving, or deregistering rule execution sets
    in multi-threaded environments.
    """

    def __init__(self):
        self.registrations = {}
        self._lock = threading.RLock()

    def register_rule_execution_set(
        self,
        name: str,
        execution_set: RuleExecutionSet,
        properties: Optional[Dict[str, Any]] = None
    ):
        """Register a RuleExecutionSet with the administrator.
        
        Thread-safe: Can be called concurrently from multiple threads.
        """
        if properties is None:
            properties = {}
        if not name or not isinstance(name, str):
            raise RuleValidationError("URI must be a non-empty string")
        if not isinstance(execution_set, RuleExecutionSet):
            raise RuleValidationError(
                f"execution_set must be a RuleExecutionSet instance, got {type(execution_set).__name__}"
            )
        with self._lock:
            self.registrations[name] = execution_set

    def deregister_rule_execution_set(
        self,
        name: str,
        properties: Optional[Dict[str, Any]] = None
    ):
        """Remove a RuleExecutionSet registration.
        
        Thread-safe: Can be called concurrently from multiple threads.
        """
        if properties is None:
            properties = {}
        with self._lock:
            self.registrations.pop(name, None)

    def get_registrations(self) -> Dict[str, RuleExecutionSet]:
        """Get all registered RuleExecutionSets.
        
        Thread-safe: Can be called concurrently from multiple threads.
        """
        with self._lock:
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
        """Create a rule session for executing rules.
        
        Args:
            uri: The URI of the registered rule execution set
            properties: Optional properties (for JSR-94 compatibility)
            stateless: If True, creates a stateless session that clears facts after execute()
        """
        if properties is None:
            properties = {}
        execution_set = self.administrator.registrations.get(uri)
        if not execution_set:
            msg = f"No rule execution set registered for URI: {uri}"
            raise RuleValidationError(msg)
        return MachineRuleSession(execution_set, stateless=stateless)

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
