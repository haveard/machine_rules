# Machine Rules API Documentation

Complete API reference for the Machine Rules engine, a JSR-94 compatible rule engine for Python.

## 📋 Table of Contents

- [Core API](#core-api)
  - [RuleServiceProviderManager](#ruleserviceprovidermanager)
  - [RuleServiceProvider](#ruleserviceprovider)
  - [RuleAdministrator](#ruleadministrator)
  - [RuleRuntime](#ruleruntime)
  - [RuleSession](#rulesession)
- [Rules and Execution Sets](#rules-and-execution-sets)
  - [Rule](#rule)
  - [RuleExecutionSet](#ruleexecutionset)
- [Loaders](#loaders)
  - [YAMLRuleLoader](#yamlruleloader)
- [Security](#security)
  - [safe_eval](#safe_eval)
  - [validate_expression](#validate_expression)
- [Exceptions](#exceptions)
- [Schemas](#schemas)

---

## Core API

### RuleServiceProviderManager

**Module**: `machine_rules.api.registry`

Singleton registry for managing rule service providers. Thread-safe implementation.

#### Methods

##### `get(name: str) -> RuleServiceProvider`

Retrieve a registered rule service provider by name.

**Parameters**:
- `name` (str): Name of the provider (e.g., "api")

**Returns**:
- `RuleServiceProvider`: The requested provider

**Raises**:
- `KeyError`: If provider not found

**Example**:
```python
from machine_rules.api.registry import RuleServiceProviderManager

provider = RuleServiceProviderManager.get("api")
```

##### `register(name: str, provider: RuleServiceProvider) -> None`

Register a new rule service provider.

**Parameters**:
- `name` (str): Name to register provider under
- `provider` (RuleServiceProvider): Provider instance

**Example**:
```python
from machine_rules.adapters.machine_adapter import MachineRuleServiceProvider

provider = MachineRuleServiceProvider()
RuleServiceProviderManager.register("custom", provider)
```

##### `list_providers() -> List[str]`

List all registered provider names.

**Returns**:
- `List[str]`: List of provider names

**Example**:
```python
providers = RuleServiceProviderManager.list_providers()
print(providers)  # ['api']
```

---

### RuleServiceProvider

**Module**: `machine_rules.api.runtime`

Abstract base class for rule service providers.

#### Methods

##### `get_rule_administrator() -> RuleAdministrator`

Get the rule administrator for managing rule execution sets.

**Returns**:
- `RuleAdministrator`: Administrator instance

##### `get_rule_runtime() -> RuleRuntime`

Get the rule runtime for creating execution sessions.

**Returns**:
- `RuleRuntime`: Runtime instance

---

### RuleAdministrator

**Module**: `machine_rules.api.administrator`

Manages rule execution sets and their lifecycle. Thread-safe implementation.

#### Methods

##### `register_rule_execution_set(name: str, execution_set: RuleExecutionSet, properties: Optional[Dict[str, Any]] = None) -> None`

Register a rule execution set with the administrator.

**Parameters**:
- `name` (str): Unique identifier for the execution set
- `execution_set` (RuleExecutionSet): The execution set to register
- `properties` (Optional[Dict[str, Any]]): Additional properties

**Raises**:
- `RuleValidationError`: If execution set is invalid

**Example**:
```python
from machine_rules.api.registry import RuleServiceProviderManager
from machine_rules.api.execution_set import Rule, RuleExecutionSet

provider = RuleServiceProviderManager.get("api")
admin = provider.get_rule_administrator()

rules = [
    Rule(
        name="high_value",
        condition=lambda x: x.get('value') > 1000,
        action=lambda x: {'tier': 'premium'},
        priority=100
    )
]

execution_set = RuleExecutionSet("value_rules", rules)
admin.register_rule_execution_set("pricing", execution_set)
```

##### `deregister_rule_execution_set(name: str) -> None`

Remove a registered rule execution set.

**Parameters**:
- `name` (str): Name of the execution set to remove

**Example**:
```python
admin.deregister_rule_execution_set("pricing")
```

##### `get_rule_execution_set(name: str) -> RuleExecutionSet`

Retrieve a registered rule execution set.

**Parameters**:
- `name` (str): Name of the execution set

**Returns**:
- `RuleExecutionSet`: The requested execution set

**Raises**:
- `KeyError`: If execution set not found

**Example**:
```python
execution_set = admin.get_rule_execution_set("pricing")
print(f"Found {len(execution_set.rules)} rules")
```

---

### RuleRuntime

**Module**: `machine_rules.api.runtime`

Creates and manages rule execution sessions.

#### Methods

##### `create_rule_session(execution_set_name: str, properties: Optional[Dict[str, Any]] = None, session_type: int = 0) -> RuleSession`

Create a new rule execution session.

**Parameters**:
- `execution_set_name` (str): Name of registered execution set
- `properties` (Optional[Dict[str, Any]]): Session properties
- `session_type` (int): Session type (0=stateless, 1=stateful)

**Returns**:
- `RuleSession`: New session instance

**Example**:
```python
from machine_rules.api.registry import RuleServiceProviderManager

provider = RuleServiceProviderManager.get("api")
runtime = provider.get_rule_runtime()

# Create stateless session
session = runtime.create_rule_session("pricing")

# Create stateful session
stateful_session = runtime.create_rule_session(
    "pricing",
    session_type=1
)
```

---

### RuleSession

**Module**: `machine_rules.api.session`

Executes rules against facts. Automatically created by RuleRuntime.

#### Methods

##### `add_facts(facts: List[Any]) -> None`

Add facts for rule evaluation.

**Parameters**:
- `facts` (List[Any]): Facts to evaluate (typically dicts)

**Raises**:
- `SessionError`: If session is closed
- `RuleValidationError`: If facts are invalid

**Example**:
```python
session.add_facts([
    {'customer_id': 'C001', 'value': 1500},
    {'customer_id': 'C002', 'value': 500}
])
```

##### `execute(filter_obj: Optional[Any] = None) -> List[Any]`

Execute rules against all facts.

**Parameters**:
- `filter_obj` (Optional[Any]): Optional filter for rules

**Returns**:
- `List[Any]`: Results from rule actions

**Raises**:
- `SessionError`: If session is closed
- `RuleExecutionError`: If execution fails

**Example**:
```python
results = session.execute()
for result in results:
    print(f"Tier: {result['tier']}")
```

##### `get_facts() -> List[Any]`

Get all facts in the session.

**Returns**:
- `List[Any]`: Current facts

**Example**:
```python
facts = session.get_facts()
print(f"Session has {len(facts)} facts")
```

##### `close() -> None`

Close the session and release resources.

**Example**:
```python
session.close()
```

#### Context Manager Support

Sessions can be used as context managers:

```python
with runtime.create_rule_session("pricing") as session:
    session.add_facts([{'value': 1500}])
    results = session.execute()
# Session automatically closed
```

---

## Rules and Execution Sets

### Rule

**Module**: `machine_rules.api.execution_set`

Represents a single business rule.

#### Constructor

```python
Rule(
    name: str,
    condition: Union[Callable, str],
    action: Union[Callable, str],
    priority: int = 0,
    description: Optional[str] = None
)
```

**Parameters**:
- `name` (str): Unique rule identifier
- `condition` (Union[Callable, str]): Condition function or expression
- `action` (Union[Callable, str]): Action function or expression
- `priority` (int): Execution priority (higher = earlier)
- `description` (Optional[str]): Human-readable description

**Example with Callables**:
```python
rule = Rule(
    name="high_value",
    condition=lambda fact: fact.get('amount') > 1000,
    action=lambda fact: {'discount': 0.1},
    priority=100,
    description="Apply discount to high-value orders"
)
```

**Example with Expressions**:
```python
rule = Rule(
    name="high_value",
    condition="fact.get('amount') > 1000",
    action="{'discount': 0.1}",
    priority=100
)
```

#### Attributes

- `name` (str): Rule name
- `condition` (Union[Callable, str]): Condition to evaluate
- `action` (Union[Callable, str]): Action to execute
- `priority` (int): Execution priority
- `description` (Optional[str]): Description

---

### RuleExecutionSet

**Module**: `machine_rules.api.execution_set`

Collection of related rules.

#### Constructor

```python
RuleExecutionSet(
    name: str,
    rules: List[Rule],
    description: Optional[str] = None
)
```

**Parameters**:
- `name` (str): Execution set identifier
- `rules` (List[Rule]): Rules in this set
- `description` (Optional[str]): Description

**Example**:
```python
execution_set = RuleExecutionSet(
    name="order_processing",
    rules=[rule1, rule2, rule3],
    description="Rules for order processing workflow"
)
```

#### Attributes

- `name` (str): Execution set name
- `rules` (List[Rule]): List of rules
- `description` (Optional[str]): Description

---

## Loaders

### YAMLRuleLoader

**Module**: `machine_rules.loader.yaml_loader`

Loads rules from YAML files with validation.

#### Methods

##### `from_file(file_path: Union[str, Path]) -> RuleExecutionSet`

Load rules from a YAML file.

**Parameters**:
- `file_path` (Union[str, Path]): Path to YAML file

**Returns**:
- `RuleExecutionSet`: Loaded execution set

**Raises**:
- `RuleValidationError`: If YAML structure is invalid
- `FileNotFoundError`: If file doesn't exist
- `SecurityError`: If unsafe expressions detected

**Example**:
```python
from machine_rules.loader.yaml_loader import YAMLRuleLoader

execution_set = YAMLRuleLoader.from_file("rules/pricing.yaml")
print(f"Loaded {len(execution_set.rules)} rules")
```

##### `from_string(yaml_content: str) -> RuleExecutionSet`

Load rules from a YAML string.

**Parameters**:
- `yaml_content` (str): YAML content as string

**Returns**:
- `RuleExecutionSet`: Loaded execution set

**Raises**:
- `RuleValidationError`: If YAML structure is invalid
- `SecurityError`: If unsafe expressions detected

**Example**:
```python
yaml_content = """
name: "test_rules"
rules:
  - name: "rule1"
    condition: "fact.get('x') > 10"
    action: "{'result': 'high'}"
    priority: 100
"""

execution_set = YAMLRuleLoader.from_string(yaml_content)
```

#### YAML Format

```yaml
name: "execution_set_name"
description: "Optional description"
rules:
  - name: "rule_name"
    description: "Optional rule description"
    condition: "fact.get('field') > value"
    action: "{'key': 'value'}"
    priority: 100
```

---

## Security

### safe_eval

**Module**: `machine_rules.security.safe_evaluator`

Safely evaluate Python expressions in a sandboxed environment.

#### Function Signature

```python
def safe_eval(expression: str, names: Dict[str, Any]) -> Any
```

**Parameters**:
- `expression` (str): Python expression to evaluate
- `names` (Dict[str, Any]): Available variable names

**Returns**:
- `Any`: Result of evaluation

**Raises**:
- `SecurityError`: If expression contains unsafe patterns
- `ValueError`: If expression is invalid

**Blocks**:
- `__import__`, `__builtins__`
- `eval`, `exec`, `compile`
- `open`, file operations
- `lambda`, `__class__`, `__globals__`, `__code__`

**Example**:
```python
from machine_rules.security.safe_evaluator import safe_eval

result = safe_eval(
    "fact.get('amount') * 1.1",
    {'fact': {'amount': 100}}
)
# result = 110.0

# This raises SecurityError
safe_eval("__import__('os').system('ls')", {})
```

---

### validate_expression

**Module**: `machine_rules.security.safe_evaluator`

Validate an expression without evaluating it.

#### Function Signature

```python
def validate_expression(expression: str) -> bool
```

**Parameters**:
- `expression` (str): Expression to validate

**Returns**:
- `bool`: True if safe, False otherwise

**Example**:
```python
from machine_rules.security.safe_evaluator import validate_expression

assert validate_expression("1 + 1") == True
assert validate_expression("__import__('os')") == False
```

---

## Exceptions

**Module**: `machine_rules.api.exceptions`

### Exception Hierarchy

```
RuleEngineError (base)
├── RuleExecutionError
├── RuleValidationError
├── SessionError
└── SecurityError
```

### RuleEngineError

Base exception for all rule engine errors.

### RuleExecutionError

Raised when rule execution fails.

**Example**:
```python
from machine_rules.api.exceptions import RuleExecutionError

try:
    results = session.execute()
except RuleExecutionError as e:
    print(f"Execution failed: {e}")
```

### RuleValidationError

Raised when rule validation fails.

**Example**:
```python
from machine_rules.api.exceptions import RuleValidationError

try:
    execution_set = YAMLRuleLoader.from_file("invalid.yaml")
except RuleValidationError as e:
    print(f"Validation failed: {e}")
```

### SessionError

Raised for session-related errors.

**Example**:
```python
from machine_rules.api.exceptions import SessionError

try:
    session.close()
    session.execute()  # Can't execute closed session
except SessionError as e:
    print(f"Session error: {e}")
```

### SecurityError

Raised when unsafe expressions are detected.

**Example**:
```python
from machine_rules.security.safe_evaluator import safe_eval, SecurityError

try:
    safe_eval("__import__('os')", {})
except SecurityError as e:
    print(f"Security error: {e}")
```

---

## Schemas

**Module**: `machine_rules.schemas.rule_schema`

Pydantic schemas for validation.

### RuleDefinition

Schema for validating rule definitions.

**Fields**:
- `name` (str): Rule name
- `condition` (str): Condition expression
- `action` (str): Action expression
- `priority` (int): Priority (default: 0)
- `description` (Optional[str]): Description

**Validation**:
- Checks for unsafe expressions
- Validates required fields
- Ensures types are correct

**Example**:
```python
from machine_rules.schemas.rule_schema import RuleDefinition

rule_data = {
    "name": "test_rule",
    "condition": "fact.get('x') > 10",
    "action": "{'result': 'high'}",
    "priority": 100
}

rule_def = RuleDefinition(**rule_data)
```

### RuleSetDefinition

Schema for validating rule set definitions.

**Fields**:
- `name` (str): Rule set name
- `rules` (List[RuleDefinition]): List of rules
- `description` (Optional[str]): Description

**Example**:
```python
from machine_rules.schemas.rule_schema import RuleSetDefinition

ruleset_data = {
    "name": "test_ruleset",
    "rules": [rule_data1, rule_data2],
    "description": "Test rules"
}

ruleset_def = RuleSetDefinition(**ruleset_data)
```

---

## Usage Patterns

### Basic Pattern

```python
# 1. Get provider
provider = RuleServiceProviderManager.get("api")
admin = provider.get_rule_administrator()
runtime = provider.get_rule_runtime()

# 2. Register rules
execution_set = RuleExecutionSet("my_rules", rules)
admin.register_rule_execution_set("my_app", execution_set)

# 3. Execute
with runtime.create_rule_session("my_app") as session:
    session.add_facts(facts)
    results = session.execute()
```

### YAML Loading Pattern

```python
# 1. Load from YAML
execution_set = YAMLRuleLoader.from_file("rules.yaml")

# 2. Register
provider = RuleServiceProviderManager.get("api")
admin = provider.get_rule_administrator()
admin.register_rule_execution_set("yaml_rules", execution_set)

# 3. Execute
runtime = provider.get_rule_runtime()
with runtime.create_rule_session("yaml_rules") as session:
    session.add_facts(facts)
    results = session.execute()
```

### Thread-Safe Pattern

```python
import threading
from machine_rules.api.registry import RuleServiceProviderManager

def process_facts(facts):
    provider = RuleServiceProviderManager.get("api")
    runtime = provider.get_rule_runtime()
    
    with runtime.create_rule_session("shared_rules") as session:
        session.add_facts(facts)
        return session.execute()

# Safe to call from multiple threads
threads = [
    threading.Thread(target=process_facts, args=(batch,))
    for batch in batches
]

for t in threads:
    t.start()
for t in threads:
    t.join()
```

---

For more examples, see [examples.py](../examples.py) and [README.md](../README.md).
