from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from .session import RuleSession


class RuleRuntime(ABC):
    """
    Abstract base class for rule runtimes.
    Follows JSR-94 specification for RuleRuntime interface.
    """

    @abstractmethod
    def create_rule_session(
        self,
        uri: str,
        properties: Optional[Dict[str, Any]] = None,
        stateless: bool = False
    ) -> RuleSession:
        """Create a rule session for executing rules."""
        pass

    @abstractmethod
    def get_registrations(self) -> List[str]:
        """Get URIs of all registered rule execution sets."""
        pass
