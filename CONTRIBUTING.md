# Contributing to Machine Rules

Thank you for your interest in contributing to Machine Rules! This document provides guidelines and instructions for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Security](#security)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## 📜 Code of Conduct

This project follows standard open source community guidelines:

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Prioritize project goals over personal preferences

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- [UV](https://github.com/astral-sh/uv) package manager (recommended)
- Git
- Basic understanding of rule engines and JSR-94 specification

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:

```bash
git clone https://github.com/YOUR-USERNAME/machine_rules.git
cd machine_rules
```

3. Add the upstream repository:

```bash
git remote add upstream https://github.com/ORIGINAL-OWNER/machine_rules.git
```

## 🛠 Development Setup

### Using UV (Recommended)

UV is 10-100x faster than pip and is the recommended tool for development:

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a virtual environment
uv venv

# Activate the virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows

# Install the package in editable mode with dev dependencies
uv pip install -e ".[dev]"
```

### Using pip

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows

# Install the package in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Verify Installation

```bash
# Run tests to verify setup
pytest

# Check code quality
ruff check .

# Run type checking
mypy machine_rules
```

## 💻 Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Your Changes

Follow these guidelines:

- **Write Tests First (TDD)**: Follow the Test-Driven Development approach
  - Write failing tests first (RED)
  - Implement minimum code to pass (GREEN)
  - Refactor while keeping tests green (REFACTOR)

- **Code Style**: Follow PEP 8 and use type hints
- **Documentation**: Update docstrings and README as needed
- **Security**: Never introduce unsafe expression evaluation
- **Commits**: Make small, focused commits with clear messages

### 3. Commit Your Changes

Use conventional commit messages:

```bash
git commit -m "feat: add new rule execution strategy"
git commit -m "fix: resolve thread safety issue in registry"
git commit -m "docs: update API documentation"
git commit -m "test: add tests for YAML loader validation"
```

Commit types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=machine_rules --cov-report=term-missing

# Run specific test file
pytest machine_rules/tests/test_core.py

# Run specific test
pytest machine_rules/tests/test_core.py::TestRuleExecution::test_basic_execution

# Run tests in parallel (faster)
pytest -n auto
```

### Writing Tests

1. **Location**: Place tests in `machine_rules/tests/`
2. **Naming**: Use `test_*.py` for test files and `test_*` for test functions
3. **Structure**: Group related tests in classes
4. **Coverage**: Aim for >95% code coverage
5. **Fixtures**: Use pytest fixtures for common setup

Example test structure:

```python
"""
Tests for new feature.

These tests verify that the new feature works correctly.
"""

import pytest
from machine_rules.api.runtime import RuleRuntime


class TestNewFeature:
    """Test suite for new feature."""
    
    def test_basic_functionality(self):
        """Test that basic functionality works."""
        # Arrange
        runtime = RuleRuntime()
        
        # Act
        result = runtime.some_method()
        
        # Assert
        assert result is not None
    
    def test_error_handling(self):
        """Test that errors are handled properly."""
        runtime = RuleRuntime()
        
        with pytest.raises(ValueError, match="expected error"):
            runtime.invalid_operation()
```

## ✅ Code Quality

### Running Linters

```bash
# Run ruff linter
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

### Type Checking

```bash
# Run mypy
mypy machine_rules

# Check specific file
mypy machine_rules/api/runtime.py
```

### Pre-commit Checks

Before committing, ensure:

1. All tests pass: `pytest`
2. No linting errors: `ruff check .`
3. Type checking passes: `mypy machine_rules`
4. Coverage is maintained: `pytest --cov=machine_rules`

You can run all checks at once:

```bash
# Run all quality checks
pytest && ruff check . && mypy machine_rules
```

## 🔒 Security

### Security Guidelines

1. **Never use `eval()` or `exec()`**: Use `safe_eval()` from `machine_rules.security`
2. **Validate all inputs**: Use Pydantic schemas for validation
3. **Block dangerous patterns**: Check expressions for `__import__`, `__builtins__`, etc.
4. **Test security**: Add tests to `test_security.py` for any security-related code
5. **Read SECURITY.md**: Understand the security model before making changes

### Reporting Security Issues

If you discover a security vulnerability, please email the maintainers directly instead of opening a public issue.

## 📝 Pull Request Process

### Before Submitting

1. Ensure all tests pass
2. Add tests for new functionality
3. Update documentation
4. Run code quality checks
5. Rebase on latest main branch
6. Write a clear PR description

### PR Checklist

- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] Code follows style guidelines
- [ ] Type hints added
- [ ] Security implications considered
- [ ] Breaking changes documented
- [ ] Commit messages follow convention

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe the tests you ran

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] Security reviewed
```

### Review Process

1. Maintainers will review your PR
2. Address any feedback
3. Once approved, maintainers will merge
4. Your contribution will be included in the next release

## 🚢 Release Process

Releases are managed by maintainers:

1. Version bump in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release tag
4. Build and publish to PyPI
5. Create GitHub release

## 📚 Additional Resources

### Documentation

- [README.md](README.md) - Project overview and usage
- [SECURITY.md](SECURITY.md) - Security guidelines
- [examples.py](examples.py) - Code examples
- JSR-94 Specification - Java Rule Engine API specification

### Development Tools

- [UV](https://github.com/astral-sh/uv) - Fast Python package manager
- [pytest](https://docs.pytest.org/) - Testing framework
- [ruff](https://github.com/astral-sh/ruff) - Fast Python linter
- [mypy](https://mypy-lang.org/) - Static type checker
- [Pydantic](https://docs.pydantic.dev/) - Data validation

### Project Structure

```
machine_rules/
├── machine_rules/          # Main package
│   ├── api/               # JSR-94 API implementation
│   ├── adapters/          # Rule engine adapters
│   ├── loader/            # Rule loaders (YAML)
│   ├── schemas/           # Pydantic schemas
│   ├── security/          # Safe expression evaluation
│   └── tests/             # Test suite
├── examples.py            # Usage examples
├── pyproject.toml         # Package configuration
├── README.md              # Documentation
├── SECURITY.md            # Security guidelines
└── CONTRIBUTING.md        # This file
```

## 🤝 Getting Help

- **Issues**: Search existing issues or create a new one
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check README.md and code comments

## 🙏 Thank You

Your contributions make this project better for everyone. We appreciate your time and effort!
