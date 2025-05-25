"""
Machine Rules - JSR-94 Compatible Python Rules Engine

A Python implementation of the JSR-94 Java Rule Engine API specification.
Provides a standard interface for rule engines with pluggable backends.
"""

from .api.registry import RuleServiceProviderManager
from .adapters.machine_adapter import MachineRuleServiceProvider


def initialize():
    """Initialize the rule engine with default providers."""
    # Register Machine provider for different use cases
    provider = MachineRuleServiceProvider()
    RuleServiceProviderManager.register("api", provider)
    RuleServiceProviderManager.register("inmemory", provider)
    RuleServiceProviderManager.register("machine", provider)


# Auto-initialize when module is imported
initialize()

__version__ = "0.1.0"
