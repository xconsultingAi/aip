import re
from pydantic import BaseModel, field_serializer, Field, HttpUrl
from pydantic import field_validator as validator
from typing import List
from datetime import datetime
from app.core.config import settings

# SH: These are Pydantic Models used for Request & Response Validation
class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255) 
    filename: str
    content_type: str
    format: str = Field(..., description="File format (pdf, docx, txt, etc.)") 
    organization_id: int

#SH: Knowledge base out
class KnowledgeBaseOut(KnowledgeBaseCreate):
    id: int
    uploaded_at: datetime
    file_size: int
    chunk_count: int
    
    #SH: Serialize datetime
    @field_serializer("uploaded_at")
    def serialize_datetime(self, value: datetime, _info):
        return value.isoformat()

    model_config = {"from_attributes": True}

#SH: Organization knowledge count
class OrganizationKnowledgeCount(BaseModel):
    organization_id: int
    total_knowledge_bases: int
    
#SH: Knowledge base agent count 
class KnowledgeBaseAgentCount(BaseModel):
    knowledge_id: int   
    agent_count: int

    model_config = {"from_attributes": True}

#SH: Knowledge link request
class KnowledgeLinkRequest(BaseModel):
    knowledge_ids: List[int]
    chunk_count: int
    agent_id: int

#SH: Knowledge URL
class KnowledgeURL(BaseModel):
    name: str = Field(..., description="Knowledge base display name")
    url: HttpUrl = Field(..., example="https://example.com/article")
    format: str = Field(..., description="Format type (webpage, pdf, html)")
    depth: int = Field(default=1, ge=1, le=3,description="Automatically set to 1 if not provided")
    include_links: bool = Field(default=False,description="Defaults to false if not provided")

#SH: Knowledge format count
class KnowledgeFormatCount(BaseModel):
    format: str
    count: int

#SH: YouTube knowledge request
class YouTubeKnowledgeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    video_url: HttpUrl = Field(..., example="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    format: str = Field(..., description="Format type (video, audio)")

#SH: Text knowledge request
class TextKnowledgeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    text_content: str = Field(..., min_length=50, max_length=settings.MAX_TEXT_LENGTH)
    format: str = Field(..., description="Format type (text, article)")
    
    
    @validator("text_content", mode="before")
    @classmethod
    def clean_text_content(cls, v):
        if not isinstance(v, str):
            raise ValueError("text_content must be a string")
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v).strip()

#SH: Text knowledge count
class TextKnowledgeCount(BaseModel):
    organization_id: int
    total_text_knowledge: int

#SH: Video knowledge count          
class VideoKnowledgeCount(BaseModel):
    organization_id: int
    total_video_knowledge: int
    
    model_config = {"from_attributes": True}
