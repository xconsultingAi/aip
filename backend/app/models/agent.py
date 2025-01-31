from pydantic import BaseModel

#MJ: These are Pydanitc Models used for Request & Response Validation

class AgentBase(BaseModel):
    name: str
    description: str | None = None

class AgentCreate(AgentBase):
    pass

class AgentOut(AgentBase):
    id: int
    class Config:
        from_attributes  = True
