from typing import List, Optional, Literal
from pydantic import BaseModel, Field

ALLOWED_MODELS = ["gpt-4", "gpt-3.5-turbo"]

# MJ: These are Pydantic Models used for Request & Response Validation
class AgentConfigSchema(BaseModel):
    model_name: str = Field(default="gpt-4", description="Selected LLM model")
    temperature: float = Field(default=0.7, ge=0, le=1)
    max_length: int = Field(default=500, gt=0)
    system_prompt: str = Field(default="You are a helpful assistant")
    knowledge_base_ids: List[int] = Field(default=[], description="Associated knowledge base IDs")

class AgentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Agent name is compulsory")
    description: Optional[str] = Field(None, max_length=255, description="Description is optional")
    organization_id: int = Field(..., description="Organization ID is compulsory")
    config: AgentConfigSchema = Field(default_factory=AgentConfigSchema)
    
class AgentCreate(AgentBase):
    pass
    
class AgentOut(AgentBase):
    id: int
    user_id: str
    organization_id: Optional[int] = None
    config: AgentConfigSchema
    knowledge_id: Optional[int] = None
class AgentResponse(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True
