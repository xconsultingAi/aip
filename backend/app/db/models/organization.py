from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.database import Base

# SH: This database model used for Migrations & CRUD operations
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    name = Column(String, nullable=False) 
    user_id = Column(String, nullable=False)
    
    # SH:Relationships with user and agent table
    users = relationship("User", back_populates="organization") 
    agents = relationship("Agent", back_populates="organization", cascade="all, delete-orphan")
    
    # SH:Relationship with knowldge base  
    knowledge_bases = relationship("KnowledgeBase", back_populates="organization",overlaps="url_knowledge",cascade="all, delete-orphan")
    url_knowledge = relationship("URLKnowledge", back_populates="organization",overlaps="knowledge_bases",cascade="all, delete-orphan")
    youtube_knowledge = relationship("YouTubeKnowledge", back_populates="organization", overlaps="knowledge_bases", cascade="all, delete-orphan")
    text_knowledge = relationship("TextKnowledge", back_populates="organization", overlaps="knowledge_bases", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="organization", cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="organization", cascade="all, delete-orphan")