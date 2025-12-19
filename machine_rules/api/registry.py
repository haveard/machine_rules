from typing import Dict, Optional
from abc import ABC, abstractmethod

# Forward references to avoid circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .administrator import RuleAdministrator
    from .runtime import RuleRuntime


class RuleServiceProvider(ABC):
    """
    Abstract base class for rule service providers.
    Follows JSR-94 specification for RuleServiceProvider interface.
    """

    @abstractmethod
    def get_rule_administrator(self) -> "RuleAdministrator":
        """Get the rule administrator for this provider."""
        pass

    @abstractmethod
    def get_rule_runtime(self) -> "RuleRuntime":
        """Get the rule runtime for this provider."""
        pass


class RuleServiceProviderManager:
    """
    Registry for rule service providers.
    Follows JSR-94 specification for RuleServiceProviderManager.
    """

    _providers: Dict[str, RuleServiceProvider] = {}

    @classmethod
    def register(cls, uri: str, provider: RuleServiceProvider):
        """Register a rule service provider with the given URI."""
        cls._providers[uri] = provider

    @classmethod
    def get(cls, uri: str) -> Optional[RuleServiceProvider]:
        """Get a rule service provider by URI."""
        return cls._providers.get(uri)

    @classmethod
    def deregister(cls, uri: str):
        """Remove a rule service provider registration."""
        cls._providers.pop(uri, None)

    @classmethod
    def get_registered_uris(cls) -> list[str]:
        """Get all registered provider URIs."""
        return list(cls._providers.keys())
