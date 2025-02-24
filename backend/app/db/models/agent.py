from sqlalchemy import Column, Integer, String, ForeignKey, Float, Text, JSON
from sqlalchemy.orm import relationship
import json
from app.db.database import Base

# MJ: This is database model used for Migrations & CRUD operations
class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True) 
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False) 
    # SH: Column for LLM Configuration
    model_name = Column(String(50), default="gpt-4")
    temperature = Column(Float, default=0.7)
    max_length = Column(Integer, default=500)
    system_prompt = Column(Text, default="You are a helpful assistant")
    config = Column(JSON, nullable=False, server_default='{}')

    # SH: Relationships with user and organization table
    organization = relationship("Organization", back_populates="agents")
    owner = relationship("User", back_populates="agents", foreign_keys=[user_id])
    organization = relationship("Organization", back_populates="agents", foreign_keys=[organization_id])
