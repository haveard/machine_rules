from abc import ABC, abstractmethod
from typing import List, Any


class RuleSession(ABC):
    """
    Abstract base class for rule sessions.
    Follows JSR-94 specification for RuleSession interface.
    """

    @abstractmethod
    def add_facts(self, facts: List[Any]):
        """Add facts to the session."""
        pass

    @abstractmethod
    def execute(self) -> List[Any]:
        """Execute rules and return results."""
        pass

    @abstractmethod
    def close(self):
        """Close the session and release resources."""
        pass

    @abstractmethod
    def reset(self):
        """Reset the session state."""
        pass
