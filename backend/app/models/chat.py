from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# SH: These are Pydantic Models used for Request & Response Validation
class ConversationBase(BaseModel):
    title: str
    agent_id: int

class ConversationCreate(ConversationBase):
    pass

class UserConversationCount(BaseModel):
    user_id: str
    total_conversations: int

class ConversationOut(ConversationBase):
    id: int
    title: str
    user_id: str
    agent_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    message_count: int = 0

    class Config:
        from_attributes = True

class ChatMessageBase(BaseModel):
    content: str
    sender: str
    agent_id: int

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatMessageOut(ChatMessageBase):
    conversation_id: int
    id: int
    timestamp: datetime
    sequence_id: int
    status: Optional[str] = None 
    
class ConversationWithMessages(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    messages: List[ChatMessageOut]
    
    
    class Config:
        from_attributes = True
