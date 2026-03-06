# Machine Rules

A JSR-94 compatible rule engine framework for Python that provides a standard interface for rule execution with pluggable backends. Perfect for building AI agents, business logic automation, and decision management systems.

## 🚀 Features

- **JSR-94 Compatible API**: Full implementation of the Java Rule Engine API specification
- **Safe Expression Evaluation**: Secure rule evaluation using `simpleeval` sandbox (blocks code injection)
- **Multiple Rule Loaders**: Support for YAML and programmatic rule definition
- **Stateless and Stateful Sessions**: Flexible rule execution patterns
- **LangGraph v1 Integration**: Build AI agents with rule-based decision making
- **Ollama Support**: Integrate with local LLMs via Ollama for hybrid AI/rules systems
- **FastAPI REST API**: HTTP endpoints for rule execution and management
- **MCP Server**: Expose the rule engine as [Model Context Protocol](https://modelcontextprotocol.io) tools for LLM agents
- **High Performance**: Efficient rule execution with priority-based evaluation
- **Comprehensive Testing**: 140 tests, 98% coverage on core modules
- **Type Safety**: Full type hints and Pydantic schema validation
- **Python 3.9+**: Modern Python with no legacy dependencies

> **⚠️ Security Notice**: Read [SECURITY.md](SECURITY.md) before loading rules from untrusted sources.

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Usage Examples](#usage-examples)
  - [Programmatic Rules](#programmatic-rules)
  - [YAML Rules](#yaml-rules)
  - [LangGraph Integration](#langgraph-integration)
  - [LangGraph + MCP Integration](#langgraph--mcp-integration)
- [REST API](#rest-api)
- [MCP Server](#-mcp-server)
- [Advanced Usage](#advanced-usage)
- [Testing](#testing)
- [Contributing](#contributing)
- [UV Package Manager](#uv-package-manager)

## 🛠 Installation

### Using UV (Recommended)

[UV](https://github.com/astral-sh/uv) is a fast Python package manager. Install it first:

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the package
uv pip install .

# For MCP server support (requires Python 3.10+)
uv pip install -e ".[mcp]"

# For LangGraph integration (with Ollama support)
uv pip install langgraph langchain-ollama

# For development
uv pip install -e ".[dev]"
```

### Using pip

```bash
pip install .

# For MCP server support (requires Python 3.10+)
pip install -e ".[mcp]"

# For LangGraph integration (with Ollama support)
pip install langgraph langchain-ollama

# For development
pip install -e ".[dev]"
```

## ⚡ Quick Start

### Basic Rule Execution

```python
from machine_rules.api.registry import RuleServiceProviderManager
from machine_rules.api.execution_set import Rule, RuleExecutionSet

# Initialize the rule engine
provider = RuleServiceProviderManager.get("api")
admin = provider.get_rule_administrator()
runtime = provider.get_rule_runtime()

# Create a simple rule
high_value_rule = Rule(
    name="high_value_customer",
    condition=lambda customer: customer.get('annual_spend', 0) > 10000,
    action=lambda customer: {
        'tier': 'VIP',
        'benefits': ['priority_support', 'free_shipping'],
        'discount_rate': 0.15
    },
    priority=100
)

# Register and execute
execution_set = RuleExecutionSet("customer_tiers", [high_value_rule])
admin.register_rule_execution_set("customer_classification", execution_set)

# Execute rules
session = runtime.create_rule_session("customer_classification")
session.add_facts([
    {'customer_id': 'C001', 'annual_spend': 15000},
    {'customer_id': 'C002', 'annual_spend': 5000}
])

results = session.execute()
session.close()

print(results)
# Output: [{'tier': 'VIP', 'benefits': ['priority_support', 'free_shipping'], 'discount_rate': 0.15}]
```

## 🎯 Core Concepts

### Architecture

The engine follows the JSR-94 specification:

```
RuleServiceProvider
├── RuleAdministrator (manages rule lifecycle)
├── RuleRuntime (creates execution sessions)
└── RuleSession (executes rules against facts)
```

### Key Components

- **Rule**: Individual business rule with condition, action, and priority
- **RuleExecutionSet**: Collection of related rules
- **Facts**: Input data that rules evaluate against
- **Session**: Execution context (stateless or stateful)

## 📚 Usage Examples

### Programmatic Rules

Create rules directly in Python code:

```python
from machine_rules.api.registry import RuleServiceProviderManager
from machine_rules.api.execution_set import Rule, RuleExecutionSet

# Initialize provider
provider = RuleServiceProviderManager.get("api")
admin = provider.get_rule_administrator()
runtime = provider.get_rule_runtime()

# Define multiple rules with priorities
rules = [
    Rule(
        name="vip_customer",
        condition=lambda fact: fact.get('annual_spend', 0) > 50000,
        action=lambda fact: {
            'tier': 'VIP',
            'priority': 'HIGHEST',
            'perks': ['concierge', 'priority_support', 'free_shipping']
        },
        priority=100
    ),
    Rule(
        name="premium_customer", 
        condition=lambda fact: fact.get('annual_spend', 0) > 10000,
        action=lambda fact: {
            'tier': 'Premium',
            'priority': 'HIGH',
            'perks': ['priority_support', 'free_shipping']
        },
        priority=80
    ),
    Rule(
        name="standard_customer",
        condition=lambda fact: True,  # Default rule
        action=lambda fact: {
            'tier': 'Standard',
            'priority': 'NORMAL',
            'perks': ['standard_support']
        },
        priority=1
    )
]

# Register and execute
execution_set = RuleExecutionSet("customer_tiers", rules)
admin.register_rule_execution_set("customer_classification", execution_set)

# Test with different customers
customers = [
    {'customer_id': 'VIP001', 'annual_spend': 75000, 'years_active': 5},
    {'customer_id': 'PREM001', 'annual_spend': 25000, 'years_active': 3},
    {'customer_id': 'STD001', 'annual_spend': 1000, 'years_active': 1}
]

session = runtime.create_rule_session("customer_classification")
session.add_facts(customers)
results = session.execute()
session.close()

for customer, result in zip(customers, results):
    print(f"Customer {customer['customer_id']}: {result['tier']} tier")
```

### YAML Rules

Define rules in YAML for easier maintenance:

**customer_rules.yaml:**
```yaml
name: "customer_segmentation"
description: "Customer tier classification and routing rules"
rules:
  - name: "vip_by_spend"
    description: "High-spending VIP customers"
    condition: "fact.get('annual_spend', 0) > 50000"
    action: |
      {
        'segment': 'VIP',
        'priority': 'highest',
        'sla_hours': 1,
        'perks': ['personal_advisor', 'free_shipping', 'priority_queue']
      }
    priority: 100

  - name: "vip_by_loyalty"
    description: "Long-term loyal customers"
    condition: "fact.get('years_customer', 0) > 10 and fact.get('annual_spend', 0) > 5000"
    action: |
      {
        'segment': 'VIP',
        'priority': 'highest', 
        'sla_hours': 2,
        'perks': ['personal_advisor', 'loyalty_bonus']
      }
    priority: 95

  - name: "premium_customer"
    description: "Premium tier customers"
    condition: "fact.get('annual_spend', 0) > 10000 or fact.get('years_customer', 0) > 5"
    action: |
      {
        'segment': 'Premium',
        'priority': 'high',
        'sla_hours': 4,
        'perks': ['free_shipping', 'priority_queue']
      }
    priority: 50

  - name: "standard_customer"
    description: "Default customer tier"
    condition: "True"
    action: |
      {
        'segment': 'Standard',
        'priority': 'normal',
        'sla_hours': 24,
        'perks': ['standard_support']
      }
    priority: 1
```

**Usage:**
```python
from machine_rules.loader.yaml_loader import YAMLRuleLoader

# Load rules from YAML
execution_set = YAMLRuleLoader.from_file("customer_rules.yaml")

# Register with the engine
provider = RuleServiceProviderManager.get("api")
admin = provider.get_rule_administrator()
runtime = provider.get_rule_runtime()

admin.register_rule_execution_set("customer_segmentation", execution_set)

# Execute against customer data
session = runtime.create_rule_session("customer_segmentation")
session.add_facts([
    {
        'customer_id': 'C001',
        'annual_spend': 75000,
        'years_customer': 3,
        'account_type': 'business'
    }
])

results = session.execute()
session.close()
print(results[0])  # {'segment': 'VIP', 'priority': 'highest', ...}
```

### LangGraph Integration

Build AI agents that use rules for decision making (requires LangGraph v1):

```python
from typing import Dict, Any, TypedDict, List
from langgraph.graph import StateGraph, START, END
from machine_rules.api.registry import RuleServiceProviderManager
from machine_rules.api.execution_set import Rule, RuleExecutionSet

class CustomerState(TypedDict):
    """State for customer service agent."""
    customer_message: str
    customer_data: Dict[str, Any]
    tier_classification: Dict[str, Any]
    routing_decision: Dict[str, Any]
    response: str

class CustomerServiceAgent:
    def __init__(self):
        # Initialize rules engine
        self.provider = RuleServiceProviderManager.get("api")
        self.admin = self.provider.get_rule_administrator()
        self.runtime = self.provider.get_rule_runtime()
        
        self._setup_rules()
        self._build_workflow()
    
    def _setup_rules(self):
        # Customer tier rules
        tier_rules = [
            Rule(
                name="vip_tier",
                condition=lambda c: c.get('annual_spend', 0) > 10000,
                action=lambda c: {
                    'tier': 'VIP',
                    'sla_minutes': 5,
                    'agent_level': 'senior'
                },
                priority=100
            )
        ]
        
        # Routing rules
        routing_rules = [
            Rule(
                name="emergency_route",
                condition=lambda inquiry: any(
                    word in inquiry.get('message', '').lower()
                    for word in ['emergency', 'critical', 'down']
                ) and inquiry.get('tier') == 'VIP',
                action=lambda inquiry: {
                    'route_to': 'emergency_team',
                    'escalate': True,
                    'response_type': 'emergency'
                },
                priority=100
            )
        ]
        
        # Register rule sets
        self.admin.register_rule_execution_set(
            "tiers", 
            RuleExecutionSet("customer_tiers", tier_rules)
        )
        self.admin.register_rule_execution_set(
            "routing",
            RuleExecutionSet("inquiry_routing", routing_rules)
        )
    
    def _build_workflow(self):
        workflow = StateGraph(CustomerState)
        
        workflow.add_node("classify_customer", self._classify_customer)
        workflow.add_node("route_inquiry", self._route_inquiry)
        workflow.add_node("generate_response", self._generate_response)
        
        # LangGraph v1 uses START constant instead of set_entry_point
        workflow.add_edge(START, "classify_customer")
        workflow.add_edge("classify_customer", "route_inquiry")
        workflow.add_edge("route_inquiry", "generate_response")
        workflow.add_edge("generate_response", END)
        
        self.workflow = workflow.compile()
    
    def _classify_customer(self, state: CustomerState) -> CustomerState:
        session = self.runtime.create_rule_session("tiers")
        session.add_facts([state["customer_data"]])
        results = session.execute()
        session.close()
        
        tier_info = results[0] if results else {'tier': 'Standard'}
        
        return {**state, "tier_classification": tier_info}
    
    def _route_inquiry(self, state: CustomerState) -> CustomerState:
        inquiry_fact = {
            "message": state["customer_message"],
            "tier": state["tier_classification"]["tier"]
        }
        
        session = self.runtime.create_rule_session("routing")
        session.add_facts([inquiry_fact])
        results = session.execute()
        session.close()
        
        routing_info = results[0] if results else {
            'route_to': 'general_support',
            'response_type': 'general'
        }
        
        return {**state, "routing_decision": routing_info}
    
    def _generate_response(self, state: CustomerState) -> CustomerState:
        tier = state["tier_classification"]
        routing = state["routing_decision"]
        
        if routing["response_type"] == "emergency":
            response = f"URGENT: As a {tier['tier']} customer, connecting you immediately to our emergency team."
        else:
            response = f"Hello! As a {tier['tier']} customer, I'm here to help you."
        
        return {**state, "response": response}
    
    def process_inquiry(self, message: str, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        initial_state = CustomerState(
            customer_message=message,
            customer_data=customer_data,
            tier_classification={},
            routing_decision={},
            response=""
        )
        
        result = self.workflow.invoke(initial_state)
        return {
            "response": result["response"],
            "tier": result["tier_classification"],
            "routing": result["routing_decision"]
        }

# Usage
agent = CustomerServiceAgent()
result = agent.process_inquiry(
    "My system is down! This is an emergency!",
    {"customer_id": "VIP001", "annual_spend": 25000}
)
print(result["response"])  # "URGENT: As a VIP customer, connecting you immediately..."
```

### LangGraph + MCP Integration

Connect a LangGraph agent to the rule engine through the MCP server — rules are
registered via `register_rule_set` and executed via `execute_rules`, all over
the Model Context Protocol:

```python
import asyncio
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import TypedDict, Dict, Any, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_ollama import ChatOllama

# Import helpers from the MCP example
from langgraph_mcp_example import mcp_rules_client, MCPRulesClient

class State(TypedDict):
    customer: Dict[str, Any]
    message: str
    tier: Dict[str, Any]
    response: str
    messages: List[BaseMessage]

async def run():
    async with mcp_rules_client() as client:
        # Register rules via MCP
        await client.register_rule_set(
            name="tiers",
            strategy="FIRST_MATCH",
            rules=[
                {
                    "name": "vip",
                    "condition": "fact.get('total_spent', 0) > 10000",
                    "action": "{'tier': 'VIP', 'greeting': 'Welcome back, VIP!'}",
                    "priority": 100,
                },
                {
                    "name": "standard",
                    "condition": "True",
                    "action": "{'tier': 'Standard', 'greeting': 'How can we help?'}",
                    "priority": 1,
                },
            ],
        )

        # Execute rules through MCP transport
        results = await client.execute_rules(
            "tiers", [{"id": "C001", "total_spent": 15000}]
        )
        print(results[0])  # {'tier': 'VIP', 'greeting': 'Welcome back, VIP!'}

asyncio.run(run())
```

See [`langgraph_mcp_example.py`](langgraph_mcp_example.py) for the full
example including a complete LangGraph state machine, Ollama LLM response
generation, and direct MCP tool usage.

## 🌐 REST API

Start the FastAPI server:

```bash
# Method 1: Using module
python -m machine_rules

# Method 2: Using uvicorn directly
uvicorn machine_rules.__main__:app --reload --port 8000

# Method 3: Production deployment
uvicorn machine_rules.__main__:app --host 0.0.0.0 --port 8000
```

### API Endpoints

#### Execute Rules
```bash
POST /execute
```

**Request:**
```json
{
  "ruleset_uri": "customer_classification",
  "facts": [
    {
      "customer_id": "C001",
      "annual_spend": 25000,
      "years_customer": 3
    }
  ]
}
```

**Response:**
```json
{
  "results": [
    {
      "tier": "Premium",
      "priority": "HIGH",
      "perks": ["priority_support", "free_shipping"]
    }
  ],
  "execution_time_ms": 45,
  "rules_executed": 3
}
```

#### List Available Rulesets
```bash
GET /rulesets
```

**Response:**
```json
{
  "rulesets": [
    "customer_classification",
    "product_recommendations", 
    "pricing_rules"
  ]
}
```

### API Usage Examples

**Python requests:**
```python
import requests

# Execute rules
response = requests.post("http://localhost:8000/execute", json={
    "ruleset_uri": "customer_classification",
    "facts": [{"annual_spend": 75000, "account_type": "premium"}]
})

result = response.json()
print(result["results"])
```

**cURL:**
```bash
# Execute customer classification
curl -X POST "http://localhost:8000/execute" \
     -H "Content-Type: application/json" \
     -d '{
       "ruleset_uri": "customer_classification",
       "facts": [{"annual_spend": 120000, "years_customer": 5}]
     }'

# List available rulesets
curl -X GET "http://localhost:8000/rulesets"
```

**JavaScript/Fetch:**
```javascript
const response = await fetch('http://localhost:8000/execute', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    ruleset_uri: 'customer_classification',
    facts: [{annual_spend: 50000, years_customer: 2}]
  })
});

const result = await response.json();
console.log(result.results);
```

## 🤖 MCP Server

The rule engine ships with a [Model Context Protocol](https://modelcontextprotocol.io)
(MCP) server that exposes all rule-management capabilities as tools and resources
that LLM agents can call directly.

### Starting the MCP server

```bash
# stdio transport (used by MCP clients such as Claude Desktop)
python -m machine_rules.mcp_server

# or via the mcp CLI
mcp run machine_rules/mcp_server.py
```

### Available tools

| Tool | Description |
|---|---|
| `register_rule_set` | Register a new rule execution set |
| `execute_rules` | Execute a registered rule set against a list of facts |
| `list_rule_sets` | List all registered rule set names |
| `get_rule_set` | Retrieve rule set metadata |
| `deregister_rule_set` | Remove a registered rule set |
| `check_expression` | Validate that an expression is safe to evaluate |

### Available resources

| URI template | Description |
|---|---|
| `rules://{name}` | Read a registered rule set as JSON |

### Claude Desktop configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "machine-rules": {
      "command": "python",
      "args": ["-m", "machine_rules.mcp_server"]
    }
  }
}
```

### In-process usage (Python)

Use the in-memory transport from `langgraph_mcp_example.py` to embed the MCP
client and server in the same process — ideal for testing and single-process
deployments (no `subprocess` required).

## 🔧 Advanced Usage

### Stateful vs Stateless Sessions

**Stateless Session (default):**
```python
# Each execution is independent
session = runtime.create_rule_session("ruleset_name")
session.add_facts([fact1, fact2])
results = session.execute()  # Rules see fact1 and fact2
session.close()

session = runtime.create_rule_session("ruleset_name") 
session.add_facts([fact3])
results = session.execute()  # Rules only see fact3
session.close()
```

**Stateful Session:**
```python
# Facts accumulate across executions
session = runtime.create_rule_session("ruleset_name", stateful=True)
session.add_facts([fact1])
results1 = session.execute()  # Rules see fact1

session.add_facts([fact2])
results2 = session.execute()  # Rules see fact1 AND fact2

session.clear_facts()  # Remove all facts
session.close()
```

### Dynamic Rule Management

**Add rules at runtime:**
```python
# Create new rule
new_rule = Rule(
    name="late_night_support",
    condition=lambda fact: fact.get('hour', 0) > 22 or fact.get('hour', 0) < 6,
    action=lambda fact: {'route_to': 'after_hours_team'},
    priority=90
)

# Get existing rules and add new one
existing_ruleset = admin.get_registrations()["customer_routing"]
updated_rules = list(existing_ruleset.get_rules()) + [new_rule]
new_ruleset = RuleExecutionSet("updated_routing", updated_rules)

# Re-register with updated rules
admin.register_rule_execution_set("customer_routing", new_ruleset)
```

**Remove rules:**
```python
# Filter out specific rules
existing_ruleset = admin.get_registrations()["customer_routing"]
filtered_rules = [
    rule for rule in existing_ruleset.get_rules() 
    if rule.name != "rule_to_remove"
]
new_ruleset = RuleExecutionSet("filtered_routing", filtered_rules)
admin.register_rule_execution_set("customer_routing", new_ruleset)
```

### Rule Priorities and Execution Order

Rules execute in priority order (higher numbers first):

```python
rules = [
    Rule("emergency", lambda f: f.get('urgent'), lambda f: {'priority': 1}, 100),
    Rule("vip", lambda f: f.get('vip'), lambda f: {'priority': 2}, 90),
    Rule("standard", lambda f: True, lambda f: {'priority': 3}, 10)
]

# Execution order: emergency → vip → standard
# First matching rule wins (unless multiple rules can fire)
```

### Error Handling and Validation

```python
try:
    # Rule execution with error handling
    session = runtime.create_rule_session("ruleset")
    session.add_facts([{"invalid": "data"}])
    results = session.execute()
    
except Exception as e:
    print(f"Rule execution failed: {e}")
    # Handle rule errors appropriately
    
finally:
    if 'session' in locals():
        session.close()
```

### Performance Optimization

**Batch Processing:**
```python
# Process multiple facts efficiently
large_batch = [generate_customer_data(i) for i in range(1000)]

session = runtime.create_rule_session("customer_classification")
session.add_facts(large_batch)
results = session.execute()  # Process all 1000 customers at once
session.close()
```

**Rule Optimization:**
```python
# Use specific conditions to avoid unnecessary evaluations
Rule(
    name="high_value_recent",
    condition=lambda f: (
        f.get('annual_spend', 0) > 50000 and  # Check expensive condition first
        f.get('last_purchase_days', 999) < 30  # Then cheaper condition
    ),
    action=lambda f: {'offer': 'premium_upgrade'},
    priority=80
)
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest machine_rules/tests/

# Run with verbose output
pytest machine_rules/tests/ -v

# Run specific test file
pytest machine_rules/tests/test_core.py -v

# Run MCP server unit tests
pytest machine_rules/tests/test_mcp_server.py -v

# Run MCP protocol round-trip integration tests
pytest machine_rules/tests/test_mcp_integration.py -v

# Run with coverage
pytest machine_rules/tests/ --cov=machine_rules --cov-report=html

# Run specific test
pytest machine_rules/tests/test_integration.py::TestYAMLLoaderIntegration::test_complex_yaml_rules_end_to_end -v
```

### Writing Custom Tests

```python
import pytest
from machine_rules.api.registry import RuleServiceProviderManager
from machine_rules.api.execution_set import Rule, RuleExecutionSet

def test_custom_rules():
    # Setup
    provider = RuleServiceProviderManager.get("api")
    admin = provider.get_rule_administrator()
    runtime = provider.get_rule_runtime()
    
    # Create test rule
    test_rule = Rule(
        name="test_rule",
        condition=lambda fact: fact.get('value', 0) > 100,
        action=lambda fact: {'result': 'high_value'},
        priority=50
    )
    
    # Register
    execution_set = RuleExecutionSet("test_rules", [test_rule])
    admin.register_rule_execution_set("test", execution_set)
    
    # Execute
    session = runtime.create_rule_session("test")
    session.add_facts([{'value': 150}])
    results = session.execute()
    session.close()
    
    # Assert
    assert len(results) == 1
    assert results[0]['result'] == 'high_value'
```

## 🚀 Examples

Run the comprehensive examples:

```bash
# Core rule engine examples (programmatic, YAML, complex business logic)
python examples.py

# LangGraph integration with Ollama (requires Ollama running with gpt-oss:20b)
ollama pull gpt-oss:20b  # First time only
python langraph_example.py

# LangGraph + MCP client example (demonstrates both direct MCP usage and
# a LangGraph state machine backed by the MCP server)
python langgraph_mcp_example.py
```

> **Note**: The LangGraph examples require [Ollama](https://ollama.ai) to be installed and running with the `gpt-oss:20b` model. The MCP example (`langgraph_mcp_example.py`) also requires `pip install ".[mcp]"`.

### Example Output

```
================================================================================
  Machine Rules Engine - JSR-94 Compatible Examples
  Demonstrating rule-based decision making in Python
================================================================================

🔧 Rules engine initialized with providers:
   • api
   • inmemory
   • machine

=== Programmatic Rules Example ===
Demonstrating: Creating rules with Python functions

📊 Processed 4 customers:
----------------------------------------------------------------------
1. VIP customer: John Doe - Income $150,000
   Category: HIGH_INCOME | Discount: 15.0% | Credit Limit: $50,000
2. Standard customer: Jane Smith - Income $75,000
   Category: STANDARD | Discount: 5.0% | Credit Limit: $10,000

=== YAML Rules Example ===
Demonstrating: Loading rules from YAML configuration

📈 Customer Segmentation Results:
----------------------------------------------------------------------
👤 VIP Customer         | VIP        | Bonus: $1000
   Perks: free_shipping, personal_advisor, early_access
👤 Premium Customer    | Premium    | Bonus: $250
   Perks: free_shipping, priority_support

=== Complex Business Logic Example ===
Demonstrating: Multi-criteria loan approval decision

💳 Loan Application Decisions:
--------------------------------------------------------------------------------
✅ Alice Premium        | Score: 780 | Income: $120,000
   Decision: APPROVED        | Rate: 3.5% | Max: $500,000
   Reason: Excellent credit and financial profile

✅ All Examples Completed Successfully
```

## 📁 Project Structure

```
machine_rules/
├── __init__.py                 # Package initialization
├── __main__.py                 # FastAPI application entry point
├── mcp_server.py               # MCP server (FastMCP tools + resource)
├── api/                        # JSR-94 API implementation
│   ├── administrator.py        # Rule management
│   ├── execution_set.py        # Rule collections
│   ├── registry.py             # Provider registry
│   ├── runtime.py              # Rule execution runtime
│   └── session.py              # Execution sessions
├── adapters/                   # Backend adapters
│   └── machine_adapter.py      # Machine rules engine adapter
├── loader/                     # Rule loaders
│   └── yaml_loader.py          # YAML rule definitions
├── security/                   # Security modules
│   └── safe_evaluator.py       # Safe expression evaluation
├── schemas/                    # Data validation
│   └── rule_schema.py          # Pydantic schemas
└── tests/                      # Test suite
    ├── test_core.py            # Core functionality tests
    ├── test_api.py             # API tests
    ├── test_integration.py     # Integration tests
    ├── test_loaders.py         # Loader tests
    ├── test_mcp_server.py      # MCP server unit tests
    └── test_mcp_integration.py # MCP protocol round-trip tests
```

## 🤝 Contributing

### Development Setup

#### Using UV (Recommended)

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/haveard/machine_rules.git
cd machine_rules

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=machine_rules

# Format code
ruff check .
ruff format .
```

#### Using pip

```bash
# Clone repository
git clone https://github.com/haveard/machine_rules.git
cd machine_rules

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode (includes MCP and API extras)
pip install -e ".[dev]"

# Run tests
pytest

# Format code
ruff check .
ruff format .
```

### Adding New Features

1. **Create a feature branch**
2. **Write tests first** (TDD approach)
3. **Implement the feature**
4. **Update documentation**
5. **Submit pull request**

### Code Style

- Use **Ruff** for code formatting and linting
- Follow **PEP 8** standards
- Write **type hints** for all functions
- Include **docstrings** for public APIs
- Maintain **test coverage > 90%**

## 📄 License

MIT License - see LICENSE file for details.

## 🙋‍♀️ Support

- **Documentation**: This README and inline code documentation
- **Security**: See [SECURITY.md](SECURITY.md) for security best practices
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines
- **Examples**: See `examples.py`, `langraph_example.py`, and `langgraph_mcp_example.py` for comprehensive usage examples
- **Tests**: Comprehensive test suite in `machine_rules/tests/`
- **Issues**: Submit bug reports and feature requests via GitHub issues

## 🔮 Roadmap

**Completed:**
- ✅ Safe expression evaluation (simpleeval)
- ✅ YAML rule loader
- ✅ LangGraph v1 integration
- ✅ Ollama/LLM support
- ✅ FastAPI REST API
- ✅ MCP server with 6 tools + resource (FastMCP)
- ✅ LangGraph + MCP client example
- ✅ Comprehensive test suite (140 tests, 98% coverage on core modules)

**Planned:**
- [ ] Rule versioning and rollback
- [ ] Performance profiling and optimization tools
- [ ] Rule execution metrics and analytics
- [ ] Additional LLM integrations (OpenAI, Anthropic)
- [ ] Docker/Kubernetes deployment templates
- [ ] Web UI for rule management

## 📦 UV Package Manager

This project uses [UV](https://github.com/astral-sh/uv) for fast, reliable Python package management.

### Benefits
- ⚡ **10-100x faster** than pip
- 🔒 **Lock file support** for reproducible builds  
- 🎯 **Smart dependency resolution**
- 💚 **Drop-in pip replacement**

### Quick Start
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup project
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

---

**Happy Rule Building!** 🎉