"""
Custom exception classes for the Machine Rules Engine.

This module defines a hierarchy of exceptions for better error handling
and more informative error messages throughout the rules engine.
"""


class RuleEngineError(Exception):
    """Base exception for all rule engine errors."""

    pass


class RuleExecutionError(RuleEngineError):
    """Exception raised when rule execution fails."""

    pass


class RuleValidationError(RuleEngineError):
    """Exception raised when rule validation fails."""

    pass


class SessionError(RuleEngineError):
    """Exception raised for session-related errors (e.g., closed session)."""

    pass
