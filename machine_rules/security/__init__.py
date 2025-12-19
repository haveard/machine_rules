"""
Security module for Machine Rules Engine.

This module provides safe expression evaluation to prevent code injection attacks.
"""

from .safe_evaluator import safe_eval, SecurityError

__all__ = ['safe_eval', 'SecurityError']
