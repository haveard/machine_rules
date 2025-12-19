"""
Security tests for Machine Rules Engine

These tests verify that security vulnerabilities are properly blocked.
All tests should PASS to ensure the system is secure.
"""

import pytest
from pathlib import Path


# DMN loader security tests removed - DMN loader has been completely removed from the project


class TestSafeExpressionEvaluator:
    """Test safe expression evaluator blocks dangerous operations."""

    def test_safe_eval_allows_safe_expressions(self):
        """Test that normal rule expressions work."""
        from machine_rules.security.safe_evaluator import safe_eval
        
        result = safe_eval("fact.get('value') > 100", {'fact': {'value': 150}})
        assert result
        
        result = safe_eval("fact.get('value') > 100", {'fact': {'value': 50}})
        assert not result

    def test_safe_eval_blocks_builtins_access(self):
        """Test that __builtins__ access is blocked."""
        from machine_rules.security.safe_evaluator import safe_eval, SecurityError
        
        with pytest.raises(SecurityError):
            safe_eval("__builtins__.__import__('os').system('ls')", {})

    def test_safe_eval_blocks_dunder_access(self):
        """Test that dunder method access is blocked."""
        from machine_rules.security.safe_evaluator import safe_eval, SecurityError
        
        with pytest.raises(SecurityError):
            safe_eval("().__class__.__bases__[0].__subclasses__()", {})

    def test_safe_eval_blocks_exec_eval(self):
        """Test that eval/exec are not accessible."""
        from machine_rules.security.safe_evaluator import safe_eval, SecurityError
        
        with pytest.raises(SecurityError):
            safe_eval("eval('1+1')", {})
        
        with pytest.raises(SecurityError):
            safe_eval("exec('print(1)')", {})

    def test_safe_eval_blocks_import(self):
        """Test that import statements are blocked."""
        from machine_rules.security.safe_evaluator import safe_eval, SecurityError
        
        with pytest.raises(SecurityError):
            safe_eval("__import__('os')", {})

    def test_safe_eval_blocks_file_operations(self):
        """Test that file operations are blocked."""
        from machine_rules.security.safe_evaluator import safe_eval, SecurityError
        
        with pytest.raises(SecurityError):
            safe_eval("open('/etc/passwd')", {})
    
    def test_safe_eval_invalid_expression_type(self):
        """Test that non-string expressions are rejected."""
        from machine_rules.security.safe_evaluator import safe_eval
        
        with pytest.raises(ValueError, match="Expression must be a string"):
            safe_eval(123, {})  # type: ignore
        
        with pytest.raises(ValueError, match="Expression must be a string"):
            safe_eval(['x', '+', 'y'], {})  # type: ignore
    
    def test_safe_eval_empty_expression(self):
        """Test that empty expressions are rejected."""
        from machine_rules.security.safe_evaluator import safe_eval
        
        with pytest.raises(ValueError, match="Expression cannot be empty"):
            safe_eval("", {})
        
        with pytest.raises(ValueError, match="Expression cannot be empty"):
            safe_eval("   ", {})
    
    def test_safe_eval_blocks_lambda(self):
        """Test that lambda expressions are blocked."""
        from machine_rules.security.safe_evaluator import safe_eval, SecurityError
        
        with pytest.raises(SecurityError, match="lambda"):
            safe_eval("lambda x: x + 1", {})
    
    def test_safe_eval_blocks_compile(self):
        """Test that compile is blocked."""
        from machine_rules.security.safe_evaluator import safe_eval, SecurityError
        
        # Note: 'compile' contains 'eval' so it matches 'eval' pattern first
        with pytest.raises(SecurityError, match="dangerous pattern"):
            safe_eval("compile('1+1', 'string', 'eval')", {})
    
    def test_safe_eval_blocks_globals_access(self):
        """Test that __globals__ access is blocked."""
        from machine_rules.security.safe_evaluator import safe_eval, SecurityError
        
        with pytest.raises(SecurityError, match="__globals__"):
            safe_eval("(lambda: None).__globals__", {})
    
    def test_safe_eval_blocks_code_access(self):
        """Test that __code__ access is blocked."""
        from machine_rules.security.safe_evaluator import safe_eval, SecurityError
        
        with pytest.raises(SecurityError, match="__code__"):
            safe_eval("(lambda: None).__code__", {})
    
    def test_safe_eval_undefined_name(self):
        """Test that undefined names raise SecurityError."""
        from machine_rules.security.safe_evaluator import safe_eval, SecurityError
        
        with pytest.raises(SecurityError, match="undefined or unsafe names"):
            safe_eval("undefined_variable", {})
    
    def test_safe_eval_undefined_function(self):
        """Test that undefined functions raise SecurityError."""
        from machine_rules.security.safe_evaluator import safe_eval, SecurityError
        
        with pytest.raises(SecurityError, match="undefined or unsafe names"):
            safe_eval("undefined_function()", {})
    
    def test_safe_eval_invalid_syntax(self):
        """Test that syntax errors are caught."""
        from machine_rules.security.safe_evaluator import safe_eval
        
        with pytest.raises(ValueError, match="Invalid expression syntax"):
            safe_eval("x +", {'x': 1})
    
    def test_safe_eval_general_error(self):
        """Test that general errors are caught and wrapped."""
        from machine_rules.security.safe_evaluator import safe_eval, SecurityError
        
        # Division by zero should be caught and wrapped
        with pytest.raises(SecurityError, match="Expression evaluation failed"):
            safe_eval("1 / 0", {})


class TestValidateExpression:
    """Test expression validation function."""
    
    def test_validate_expression_safe(self):
        """Test that safe expressions with valid values validate successfully."""
        from machine_rules.security.safe_evaluator import validate_expression
        
        # Expressions with literal values validate
        assert validate_expression("1 + 1")
        assert validate_expression("True and False")
        assert validate_expression("'hello' + 'world'")
    
    def test_validate_expression_undefined_names(self):
        """Test that expressions with undefined names fail validation."""
        from machine_rules.security.safe_evaluator import validate_expression
        
        # Undefined names raise SecurityError, so validation fails
        assert not validate_expression("x + y")
        assert not validate_expression("fact.get('value') > 100")
    
    def test_validate_expression_unsafe(self):
        """Test that unsafe expressions fail validation."""
        from machine_rules.security.safe_evaluator import validate_expression
        
        assert not validate_expression("__import__('os')")
        assert not validate_expression("eval('1+1')")
        assert not validate_expression("")


class TestSecurityDocumentation:
    """Test that security documentation exists."""

    def test_security_documentation_exists(self):
        """SECURITY.md must exist."""
        assert Path("SECURITY.md").exists(), "SECURITY.md file must exist"

    def test_security_documentation_content(self):
        """SECURITY.md must contain key security information."""
        content = Path("SECURITY.md").read_text().lower()
        
        assert "eval" in content, "Must discuss eval security"
        assert "trust" in content, "Must discuss trust model"
        assert "safe" in content, "Must discuss safe practices"
        assert "yaml" in content, "Must discuss YAML loader"
        assert "dmn" in content, "Must discuss DMN loader"
