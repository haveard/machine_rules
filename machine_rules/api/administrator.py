from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .execution_set import RuleExecutionSet


class RuleAdministrator(ABC):
    """
    Abstract base class for rule administrators.
    Follows JSR-94 specification for RuleAdministrator interface.
    """

    @abstractmethod
    def register_rule_execution_set(
        self,
        name: str,
        execution_set: RuleExecutionSet,
        properties: Optional[Dict[str, Any]] = None
    ):
        """Register a RuleExecutionSet with the administrator."""
        pass

    @abstractmethod
    def deregister_rule_execution_set(
        self,
        name: str,
        properties: Optional[Dict[str, Any]] = None
    ):
        """Remove a RuleExecutionSet registration."""
        pass

    @abstractmethod
    def get_registrations(self) -> Dict[str, RuleExecutionSet]:
        """Get all registered RuleExecutionSets."""
        pass
