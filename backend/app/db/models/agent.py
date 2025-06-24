from sqlalchemy import Column, Integer, String, ForeignKey, Float, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.db.models.knowledge_base import agent_knowledge

# MJ: This is database model used for Migrations & CRUD operations
class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True) 
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    url_id = Column(Integer, ForeignKey("url_knowledge.id"), nullable=True)
    # SH: Column for LLM Configuration
    model_name = Column(String(50), default="gpt-4")
    temperature = Column(Float, default=0.7)
    max_length = Column(Integer, default=500)
    system_prompt = Column(Text, default="You are a helpful assistant")
    config = Column(JSON, nullable=False, server_default='{}')
    # Advanced configuration
    context_window_size = Column(Integer, default=2000)
    response_throttling = Column(Float, default=0.0)
    domain_focus = Column(String(50), default="general")
    enable_fallback = Column(Boolean, default=True)
    max_retries = Column(Integer, default=2)
    
    #SH: Column for Widget
    greeting_message = Column(String(200), default="Hello! How can I help?")
    theme_color = Column(String(7), default="#22c55e")  # Hex format
    embed_code = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    # SH: Relationships with user and organization table
    knowledge_bases = relationship("KnowledgeBase", secondary=agent_knowledge, back_populates="agents",overlaps="url_knowledge")
    owner = relationship("User", back_populates="agents")
    organization = relationship("Organization", back_populates="agents")
    chat_messages = relationship("ChatMessage", back_populates="agent")
    conversations = relationship("Conversation", back_populates="agent")
    widget_sessions = relationship("WidgetSession", back_populates="agent", cascade="all, delete-orphan")
    url_knowledge = relationship("URLKnowledge", back_populates="agents", overlaps="knowledge_bases")
    youtube_knowledge = relationship("YouTubeKnowledge", back_populates="agents", overlaps="knowledge_bases")
    text_knowledge = relationship("TextKnowledge", back_populates="agents", overlaps="knowledge_bases")

