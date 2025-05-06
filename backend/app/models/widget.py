from pydantic import BaseModel
from datetime import datetime

class WidgetSessionBase(BaseModel):
    visitor_id: str
    agent_id: int

class WidgetSessionCreate(WidgetSessionBase):
    pass

class WidgetSessionOut(WidgetSessionBase):
    id: int
    started_at: datetime
    last_active: datetime
    message_count: int
    status: str

    class Config:
        from_attributes = True

class WidgetMessage(BaseModel):
    content: str
    sender: str  # "visitor" or "agent"
    timestamp: datetime