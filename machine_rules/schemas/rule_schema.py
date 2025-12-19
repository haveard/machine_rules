from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import re


class RuleDefinition(BaseModel):
    """Schema for a single rule definition."""
    name: str = Field(..., min_length=1, description="Rule name")
    condition: str = Field(..., min_length=1, description="Rule condition expression")
    action: str = Field(..., min_length=1, description="Rule action expression")
    priority: int = Field(default=0, description="Rule priority (higher = executes first)")
    
    @field_validator('condition', 'action')
    @classmethod
    def validate_expression_safety(cls, v: str) -> str:
        """Validate that expressions don't contain dangerous patterns."""
        dangerous_patterns = [
            r'__import__',
            r'eval\s*\(',
            r'exec\s*\(',
            r'compile\s*\(',
            r'__builtins__',
            r'open\s*\(',
            r'file\s*\(',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(
                    f"Expression contains forbidden pattern '{pattern}' which could be unsafe. "
                    f"Use safe expressions only."
                )
        return v


class RuleSetDefinition(BaseModel):
    """Schema for a complete rule set definition."""
    name: str = Field(..., min_length=1, description="Rule set name")
    description: Optional[str] = Field(default="", description="Rule set description")
    rules: List[RuleDefinition] = Field(..., description="List of rules")
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "name": "example_rules",
                "description": "Example rule set",
                "rules": [
                    {
                        "name": "high_value_rule",
                        "condition": "fact.get('value', 0) > 100",
                        "action": "{'result': 'high'}",
                        "priority": 10
                    }
                ]
            }]
        }
    }
