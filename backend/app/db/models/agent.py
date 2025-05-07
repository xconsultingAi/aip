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
    # SH: Column for LLM Configuration
    model_name = Column(String(50), default="gpt-4")
    temperature = Column(Float, default=0.7)
    max_length = Column(Integer, default=500)
    system_prompt = Column(Text, default="You are a helpful assistant")
    config = Column(JSON, nullable=False, server_default='{}')
    #SH: Column for Widget
    greeting_message = Column(String(200), default="Hello! How can I help?")
    theme_color = Column(String(7), default="#22c55e")  # Hex format
    embed_code = Column(Text, nullable=True)

    # SH: Relationships with user and organization table
    knowledge_bases = relationship("KnowledgeBase", secondary=agent_knowledge, back_populates="agents")
    owner = relationship("User", back_populates="agents")
    organization = relationship("Organization", back_populates="agents", foreign_keys=[organization_id])
    chat_messages = relationship("ChatMessage", back_populates="agent")
    conversations = relationship("Conversation", back_populates="agent")
    widget_sessions = relationship("WidgetSession", back_populates="agent", cascade="all, delete-orphan")