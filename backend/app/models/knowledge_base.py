from pydantic import BaseModel, field_serializer
from typing import List
from datetime import datetime

class KnowledgeBaseCreate(BaseModel):
    filename: str
    content_type: str
    organization_id: int

class KnowledgeBaseOut(KnowledgeBaseCreate):
    id: int
    uploaded_at: datetime
    file_size: int
    chunk_count: int
    
    @field_serializer("uploaded_at")
    def serialize_datetime(self, value: datetime, _info):
        return value.isoformat()

    model_config = {"from_attributes": True}

class OrganizationKnowledgeCount(BaseModel):
    organization_id: int
    total_knowledge_bases: int

    model_config = {"from_attributes": True}

class KnowledgeLinkRequest(BaseModel):
    knowledge_ids: List[int]
    chunk_count: int
    agent_id: int

    model_config = {"from_attributes": True}
