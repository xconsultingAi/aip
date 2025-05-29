from pydantic import BaseModel
from datetime import datetime

# SH: These are Pydantic Models used for Request & Response Validation
class WidgetSessionBase(BaseModel):
    visitor_id: str
    agent_id: int

#SH: Widget session create
class WidgetSessionCreate(WidgetSessionBase):
    pass

#SH: Widget session out
class WidgetSessionOut(WidgetSessionBase):
    id: int
    started_at: datetime
    last_active: datetime
    message_count: int
    status: str

    class Config:
        from_attributes = True

#SH: Widget message 
class WidgetMessage(BaseModel):
    content: str
    sender: str  # "visitor" or "agent"
    timestamp: datetime