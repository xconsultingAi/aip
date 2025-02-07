from pydantic import BaseModel, Field
from typing import Optional

# MJ: These are Pydantic Models used for Request & Response Validation
class AgentBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, description="Agent name is compulsory")
    description: Optional[str] = Field(None, max_length=255, description="Description is optional")
    organization_id: int = Field(..., description="Organization ID is compulsory")

class AgentCreate(AgentBase):
    pass

class AgentOut(AgentBase):
    id: int
    user_id: str
    organization_id: Optional[int] = None

    class Config:
        from_attributes = True
