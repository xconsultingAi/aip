from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator as validator

ALLOWED_MODELS = ["gpt-4", "gpt-3.5-turbo"]

# MJ: These are Pydantic Models used for Request & Response Validation
class AgentConfigSchema(BaseModel):
    model_name: Literal["gpt-4", "gpt-3.5-turbo"] = Field(default="gpt-4", description="Selected LLM model")
    temperature: float = Field(default=0.7, ge=0, le=1)
    max_length: int = Field(default=500, gt=0)
    system_prompt: str = Field(default="You are a helpful assistant")
    knowledge_base_ids: List[int] = Field(default=[], description="Associated knowledge base IDs")
    
    # Advanced configuration options
    context_window_size: int = Field(default=2000,ge=500,le=8000,description="Maximum tokens for context memory")
    response_throttling: float = Field(default=0.0,ge=0.0,le=5.0,description="Delay in seconds between responses")
    domain_focus: str = Field(default="general",description="Primary domain specialization (e.g., finance, healthcare, customer support)")
    enable_fallback: bool = Field(default=True,description="Enable fallback to simpler model when context is too large")
    max_retries: int = Field(default=2,ge=0,le=5,description="Maximum retries for failed operations")
    
    # SH: advanced settings for widget
    greeting_message: str = Field(default="Hello! How can I help?", min_length=1, max_length=200)
    theme_color: Optional[str] = "#22c55e"
    embed_code: Optional[str] = None
    is_public: Optional[bool] = False

    # Validation for domain focus
    @validator("domain_focus")
    def validate_domain_focus(cls, value):
        if not value.replace(" ", "").isalnum():
            raise ValueError("Domain focus must be alphanumeric")
        return value.lower()

# Base Agent Model
class AgentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Agent name is compulsory")
    description: Optional[str] = Field(None, max_length=255, description="Description is optional")
    organization_id: int = Field(..., description="Organization ID is compulsory")

    greeting_message: str = Field(default="Hello! How can I help?", min_length=1,max_length=200, description="Greeting message (max 50 words)")
    theme_color: str = Field(default="#22c55e", pattern="^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$", description="Hex color code (e.g. #RRGGBB or #RGB)")
    embed_code: Optional[str] = Field(default=None, description="Custom embed code for widget")
    is_public: bool = Field(default=False, description="Make agent publicly accessible")

# Agent Creation Model
class AgentCreate(AgentBase):
    pass

# Agent Output Model
class AgentOut(AgentBase):
    id: int
    user_id: str
    organization_id: int
    config: AgentConfigSchema
    knowledge_base_ids: List[int] = Field(default=[], description="Associated knowledge base IDs")
    # SH: For Widget
    greeting_message: str
    theme_color: str
    embed_code: Optional[str]
    is_public: bool

# Agent Response Model
class AgentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    config: AgentConfigSchema

    class Config:
        from_attributes = True
