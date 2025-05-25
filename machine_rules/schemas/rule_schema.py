from pydantic import BaseModel
from typing import List, Optional, Dict


class RuleDefinition(BaseModel):
    condition: str
    action: str
    metadata: Optional[Dict] = None


class RuleSetDefinition(BaseModel):
    name: str
    rules: List[RuleDefinition]
    metadata: Optional[Dict] = None
