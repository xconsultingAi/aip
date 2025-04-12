from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# SH: These are Pydantic Models used for Request & Response Validation
class ChatMessageBase(BaseModel):
    content: str
    sender: str
    agent_id: int
    
class ChatMessageCreate(ChatMessageBase):
    pass 

class ChatMessageOut(ChatMessageBase):
    id: int
    timestamp: datetime
    delivered: bool
    read: bool 

    class Config:
        from_attributes = True