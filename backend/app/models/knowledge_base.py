import re
from pydantic import BaseModel, field_serializer, Field, HttpUrl, ConfigDict, model_validator
from pydantic import field_validator as validator
from typing import Any, List, Optional
from datetime import datetime
from app.core.config import settings

# SH: These are Pydantic Models used for Request & Response Validation
class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255) 
    filename: str
    content_type: str
    format: str = Field(..., description="File format (pdf, docx, txt, etc.)") 
    organization_id: int

# Category Models
class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    parent_id: Optional[int] = None

class CategoryCreate(CategoryBase):
    organization_id: int

class CategoryOut(CategoryBase):
    id: int
    organization_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class CategoryTree(CategoryOut):
    children: List['CategoryTree'] = []
    
    model_config = ConfigDict(from_attributes=True)

# Tag Models
class TagBase(BaseModel):
    name: str = Field(..., max_length=50)

class TagCreate(TagBase):
    organization_id: int

class TagOut(TagBase):
    id: int
    organization_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

#SH: Knowledge base out
class KnowledgeBaseOut(KnowledgeBaseCreate):
    id: int
    uploaded_at: datetime
    file_size: int
    chunk_count: int
    category: Optional[CategoryOut] = None
    tags: List[TagOut] = []

    @field_serializer("uploaded_at")
    def serialize_datetime(self, value: datetime, _info):
        return value.isoformat()

    @model_validator(mode='before')
    @classmethod
    def handle_async_relations(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        # Handle SQLAlchemy model instance
        if hasattr(data, 'tags'):
            tags = [tag for tag in data.tags] if data.tags else []
            return {
                **{field.name: getattr(data, field.name) 
                   for field in data.__table__.columns},
                'tags': tags,
                'category': getattr(data, 'category', None)
            }
        return data

    model_config = ConfigDict(from_attributes=True)

#SH: Organization knowledge count
class OrganizationKnowledgeCount(BaseModel):
    organization_id: int
    total_knowledge_bases: int
    
#SH: Knowledge base agent count 
class KnowledgeBaseAgentCount(BaseModel):
    knowledge_id: int   
    agent_count: int

    model_config = ConfigDict(from_attributes=True)

#SH: Knowledge link request
class KnowledgeLinkRequest(BaseModel):
    knowledge_ids: List[int]
    chunk_count: int
    agent_id: int

#SH: Knowledge URL
class KnowledgeURL(BaseModel):
    name: str = Field(..., description="Knowledge base display name")
    url: HttpUrl = Field(..., example="https://example.com/article")
    format: str = Field(...,description="Format type (webpage, pdf, html)", pattern=f"^({'|'.join(settings.ALLOWED_URL_FORMATS)})$",examples=settings.ALLOWED_URL_FORMATS)
    depth: int = Field(default=1, ge=1, le=3, description="Automatically set to 1 if not provided")
    include_links: bool = Field(default=False, description="Defaults to false if not provided")

#SH: Knowledge format count
class KnowledgeFormatCount(BaseModel):
    format: str
    count: int

#SH: YouTube knowledge request
class YouTubeKnowledgeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    video_url: HttpUrl = Field(..., example="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    format: str = Field(...,description="Format type (video, audio)",pattern="^(video|audio)$",examples=["video", "audio"])

#SH: Text knowledge request
class TextKnowledgeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    text_content: str = Field(..., min_length=50, max_length=settings.MAX_TEXT_LENGTH)
    format: str = Field(..., description="Format type (text, article)", pattern="^(text|article)$", examples=["text", "article"])
    @validator("text_content", mode="before")
    @classmethod
    def clean_text_content(cls, v):
        if not isinstance(v, str):
            raise ValueError("text_content must be a string")
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v).strip()
    
    model_config = ConfigDict(from_attributes=True)
    
#SH: Model for category/tags assignment
class KnowledgeUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None
    
# Add new models for search
class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=255, description="Search keywords")
    file_types: Optional[List[str]] = Field(None, description="Filter by file types")
    start_date: Optional[datetime] = Field(None, description="Start date for filtering")
    end_date: Optional[datetime] = Field(None, description="End date for filtering")
    category_id: Optional[int] = Field(None, description="Filter by category ID")
    tag_id: Optional[int] = Field(None, description="Filter by tag ID")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(10, ge=1, le=100, description="Items per page")

class KnowledgeSearchResult(BaseModel):
    id: int
    name: str
    filename: str
    content_type: str
    format: str
    uploaded_at: datetime
    file_size: int
    snippet: str
    category: Optional[CategoryOut] = None
    tags: List[TagOut] = []

    @field_serializer("uploaded_at")
    def serialize_datetime(self, value: datetime, _info):
        return value.isoformat()

class KnowledgeSearchResponse(BaseModel):
    results: List[KnowledgeSearchResult]
    total: int
    page: int
    page_size: int