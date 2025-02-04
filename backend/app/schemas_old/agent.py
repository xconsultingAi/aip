from pydantic import BaseModel, Field
from typing import Optional

#SH: Schema for creating an agent for request body
class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Agent name must be a valid string.")
    description: Optional[str] = None  # Optional field for description

#SH: Schema for returning agent data for response body
class AgentOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        orm_mode = True
