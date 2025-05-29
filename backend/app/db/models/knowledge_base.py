from dataclasses import Field
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, func, Boolean
from sqlalchemy.orm import relationship
from app.db.database import Base

#SH: This is database model used for Migrations & CRUD operations

#SH: Many-to-Many Relationship Table
agent_knowledge = Table(
    'agent_knowledge',
    Base.metadata,
    Column('agent_id', Integer, ForeignKey('agents.id', ondelete="CASCADE"), primary_key=True),
    Column('knowledge_id', Integer, ForeignKey('knowledge_bases.id', ondelete="CASCADE"), primary_key=True)
)

#SH: Base model for all knowledge bases
class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    format = Column(String(10), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)  
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    file_size = Column(Integer, nullable=False)
    chunk_count = Column(Integer, nullable=False)
    source_type = Column(String(10), default="file")

    #SH: Relationship with agents and organization
    agents = relationship("Agent", secondary=agent_knowledge, back_populates="knowledge_bases")
    organization = relationship("Organization", back_populates="knowledge_bases")
    
# For Url Scraping
class URLKnowledge(KnowledgeBase):
    __tablename__ = "url_knowledge"
    __mapper_args__ = {'polymorphic_identity': 'url_knowledge'}
    id = Column(Integer, ForeignKey('knowledge_bases.id'), primary_key=True) 
    url = Column(String(2048), nullable=False, unique=True)
    url_format = Column(String(20), nullable=False)
    file_path = Column(String(512), nullable=False)
    domain_name = Column(String(256), nullable=False)
    crawl_depth = Column(Integer, default=1, nullable=False)
    include_links = Column(Boolean, default=False, nullable=False)
    last_crawled = Column(DateTime, default=func.now(), nullable=False)
    
    
    agents = relationship("Agent", back_populates="url_knowledge", overlaps="knowledge_bases")
    organization = relationship("Organization", back_populates="url_knowledge", overlaps="knowledge_bases")

#SH: For Youtube
class YouTubeKnowledge(KnowledgeBase):
    __tablename__ = "youtube_knowledge"
    __mapper_args__ = {'polymorphic_identity': 'youtube_knowledge'}
    id = Column(Integer, ForeignKey('knowledge_bases.id'), primary_key=True)
    video_id = Column(String(20), nullable=False, unique=True)
    video_url = Column(String(512), nullable=False)
    format_data = Column(String(50), nullable=False)
    transcript_length = Column(Integer, nullable=False)
    file_path = Column(String(512), nullable=False)
    
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    agents = relationship("Agent", back_populates="youtube_knowledge", overlaps="knowledge_bases")


#SH: For Text       
class TextKnowledge(KnowledgeBase):
    __tablename__ = "text_knowledge"
    __mapper_args__ = {'polymorphic_identity': 'text_knowledge'}
    id = Column(Integer, ForeignKey('knowledge_bases.id'), primary_key=True)
    format_data = Column(String(50), nullable=False)
    content_hash = Column(String(64), nullable=False, unique=True)  # SHA-256 hash
    file_path = Column(String(512), nullable=False)
    
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    agents = relationship("Agent", back_populates="text_knowledge", overlaps="knowledge_bases")

