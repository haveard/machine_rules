# Security Policy

## Trust Model

Machine Rules is a rule engine that evaluates expressions defined in rule files. The security of your application depends on **where rules come from** and **who has access to modify them**.

### Security Levels

#### 🔒 Trusted Rules (SAFE)
Rules defined by your development team, version-controlled in your repository, and deployed with your application.

**Use Case**: Application logic, business rules maintained by developers
**Risk Level**: Low - These are equivalent to code in your application

#### ⚠️ Semi-Trusted Rules (CAUTION)
Rules authored by internal users (administrators, business analysts) through controlled interfaces.

**Use Case**: Configuration, business rules that need to change without code deployment
**Risk Level**: Medium - Requires validation and sandboxing

#### 🚫 Untrusted Rules (DANGEROUS)
Rules from external sources, user uploads, or public input.

**Use Case**: **NOT RECOMMENDED**
**Risk Level**: Critical - Can lead to arbitrary code execution

---

## Safe Rule Loading

### ✅ YAML Loader (Safe)

The YAML loader uses a **safe expression evaluator** (via `simpleeval`) that prevents code injection:

```python
from machine_rules.loader.yaml_loader import YAMLRuleLoader

# Safe: Uses simpleeval sandbox for expression evaluation
execution_set = YAMLRuleLoader.from_file('rules.yaml')
```

**What's Allowed:**
- ✅ Arithmetic: `fact.get('value') + 10`
- ✅ Comparisons: `fact.get('age') > 18`
- ✅ Dictionary/list access: `fact['items'][0]`
- ✅ Boolean logic: `x > 10 and y < 20`
- ✅ Method calls: `fact.get('name', 'default')`
- ✅ Built-in functions: `len()`, `str()`, `int()`, etc.

**What's Blocked:**
- ❌ Imports: `__import__('os')`
- ❌ File operations: `open('/etc/passwd')`
- ❌ Code execution: `eval()`, `exec()`, `compile()`
- ❌ Dunder access: `__class__`, `__builtins__`
- ❌ System calls: `os.system()`

### ✅ Programmatic Rules (Safe)

Rules created with Python functions are safe when the functions themselves are trusted:

```python
from machine_rules.api.execution_set import Rule

def check_age(fact):
    return fact.get('age', 0) >= 18

def grant_access(fact):
    return {'access': 'granted', 'user': fact.get('name')}

rule = Rule(
    name="age_verification",
    condition=check_age,
    action=grant_access
)
```

---

## Production Best Practices

### 1. Version Control All Rules

```bash
# Store rules in your repository
git add rules/production_rules.yaml
git commit -m "Update business rules"
```

### 2. Code Review Rule Changes

Treat rule changes like code changes:
- Pull request process
- Peer review
- Automated testing

### 3. Validate Rules Before Deployment

```python
from machine_rules.security.safe_evaluator import safe_eval, SecurityError
import logging

logger = logging.getLogger(__name__)

def validate_rule_expression(expr: str) -> bool:
    """Validate expression before deployment."""
    try:
        # Test with dummy data
        safe_eval(expr, {'fact': {}})
        return True
    except SecurityError as e:
        logger.error(f"Unsafe expression: {e}")
        return False
    except Exception as e:
        logger.error(f"Invalid expression: {e}")
        return False
```

### 4. Use Read-Only Permissions

In production:
- Deploy rules as read-only files
- Don't allow runtime rule modification
- Never load rules from user input

### 5. Monitor Rule Execution

```python
import logging

logging.basicConfig(level=logging.WARNING)
# Security errors in rules will be logged
```

---

## Security Features

### Safe Expression Evaluator

The safe evaluator (using `simpleeval`) provides:

1. **Restricted Namespace**: Only specified variables accessible
2. **No Imports**: Cannot load external modules
3. **No Builtins**: No access to `__builtins__`
4. **Pattern Blocking**: Rejects dangerous patterns before evaluation
5. **Exception Handling**: Graceful failures without exposing internals

### Logging

All security errors are logged:

```python
import logging

# Configure logging to track security issues
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

---

## Known Limitations

### 1. Expression Language Restrictions

The safe evaluator supports a **subset** of Python:

**Supported:**
- Arithmetic operators: `+`, `-`, `*`, `/`, `%`, `**`
- Comparison operators: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Boolean operators: `and`, `or`, `not`
- Dictionary/list access: `fact['key']`, `fact.get('key')`
- Literals: numbers, strings, lists, dicts

**Not Supported:**
- Comprehensions: `[x for x in items]`
- Lambda functions: `lambda x: x + 1`
- Complex assignments
- Control flow statements (if/else, for, while)

**Workaround**: Implement complex logic in custom action functions:

```python
def complex_action(fact):
    # Implement complex logic in Python
    items = fact.get('items', [])
    return [process(item) for item in items if item.active]

rule = Rule(
    name="complex_rule",
    condition=lambda f: f.get('type') == 'special',
    action=complex_action
)
```

### 2. Performance Considerations

Safe evaluation has minimal overhead (~10-20% slower than native eval), but for rule sets with thousands of evaluations per second, consider:
- Caching rule results
- Using programmatic rules (Python functions)
- Profiling with `cProfile`

### 3. Future Python Compatibility

The safe evaluator may need updates for new Python versions. Always test with your target Python version.

---

## Reporting Security Issues

**DO NOT** open public GitHub issues for security vulnerabilities.

Instead, please use one of these methods:

1. **GitHub Security Advisories**: Use the [Security tab](https://github.com/haveard/machine_rules/security) on the repository
2. **Email**: Contact the maintainers directly through GitHub

**Include in your report:**
- Description of the vulnerability
- Steps to reproduce
- Impact assessment
- Affected versions
- Suggested fix (if any)

We will respond within 48 hours and provide a timeline for fixes.

### Security Response Process

1. **Acknowledge**: Confirm receipt within 48 hours
2. **Assess**: Evaluate severity and impact within 1 week
3. **Fix**: Develop and test patch
4. **Disclose**: Coordinate disclosure timeline
5. **Release**: Publish fixed version and security advisory

---

## Removed Features

### DMN/Excel Loader

The DMN/Excel loader (`DMNRuleLoader`) was **completely removed** in version 0.2.0 due to irremediable security vulnerabilities:
- Used unsafe `eval()` allowing arbitrary code execution
- Could not be safely sandboxed
- Presented unacceptable security risk

**Migration Path**: Use the YAML loader for structured rule data. YAML provides:
- Safe expression evaluation via `simpleeval`
- Version-controllable plain text format
- Better testing and validation capabilities
- No Excel dependencies

---

## Dependencies

### Core Security Dependencies

The project uses these dependencies for secure operation:

- **simpleeval** (>=0.9.13): Safe expression evaluation
- **pyyaml** (>=6.0): Safe YAML parsing
- **pydantic** (>=2.0): Data validation

Install core dependencies:

```bash
pip install machine-rules
```

Or with optional API features:

```bash
pip install machine-rules[api]
```

simpleeval is a mature, well-audited library used by many projects for safe expression evaluation.

---

## Security Checklist

Before deploying to production:

- [ ] All rules stored in version control
- [ ] Rules loaded from trusted sources only (YAML files or programmatic)
- [ ] No rules loaded from user input or untrusted sources
- [ ] Logging configured to capture security errors
- [ ] Rules tested with security test suite (`pytest machine_rules/tests/test_security.py`)
- [ ] Team trained on rule security best practices
- [ ] Monitoring in place for suspicious rule activity
- [ ] Incident response plan documented
- [ ] Production environment uses read-only rule files

---

## Version History

| Version | Date | Security Changes |
|---------|------|------------------|
| 0.2.0 | 2025-12-18 | Added safe evaluator, removed DMN loader, Python 3.9+ requirement |
| 0.1.0 | 2024 | Initial release (unsafe eval in loaders) |

---

## Additional Resources

- [OWASP - Code Injection](https://owasp.org/www-community/attacks/Code_Injection)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [simpleeval Documentation](https://github.com/danthedeckie/simpleeval)
- [Machine Rules Documentation](README.md)
- [Contributing Guidelines](CONTRIBUTING.md)

---

**Last Updated**: December 18, 2025  
**Next Review**: March 18, 2026
