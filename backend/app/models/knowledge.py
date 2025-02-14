from datetime import datetime
from pydantic import BaseModel

class KnowledgeBaseBase(BaseModel):
    filename: str
    content_type: str
    organization_id: int

class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass

class KnowledgeBaseOut(KnowledgeBaseBase):
    id: int
    uploaded_at: datetime
    class Config:
        from_attributes = True
