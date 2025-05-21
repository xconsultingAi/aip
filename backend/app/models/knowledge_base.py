from pydantic import BaseModel, field_serializer, Field, HttpUrl
from typing import List
from datetime import datetime

class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255) 
    filename: str
    content_type: str
    format: str = Field(..., description="File format (pdf, docx, txt, etc.)") 
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
    
class KnowledgeURL(BaseModel):
    name: str = Field(..., description="Knowledge base display name")
    url: HttpUrl = Field(..., example="https://example.com/article")
    depth: int = Field(default=1, ge=1, le=3,description="Automatically set to 1 if not provided")
    include_links: bool = Field(default=False,description="Defaults to false if not provided")

class KnowledgeFormatCount(BaseModel):
    format: str
    count: int

    model_config = {"from_attributes": True}
