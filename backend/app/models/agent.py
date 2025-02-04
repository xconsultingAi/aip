from pydantic import BaseModel

# MJ: These are Pydantic Models used for Request & Response Validation
class AgentBase(BaseModel):
    name: str
    description: str | None = None
    organization_id:int | None = None # Added 'organization' field

class AgentCreate(AgentBase):
    pass

class AgentOut(AgentBase):
    id: int
    class Config:
        from_attributes = True
