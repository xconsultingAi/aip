from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, func, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

# Many-to-Many Relationship Table
agent_knowledge = Table(
    'agent_knowledge',
    Base.metadata,
    Column('agent_id', Integer, ForeignKey('agents.id', ondelete="CASCADE"), primary_key=True),
    Column('knowledge_id', Integer, ForeignKey('knowledge_bases.id', ondelete="CASCADE"), primary_key=True)
)
class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(50), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)  
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    file_size = Column(Integer, nullable=False)
    chunk_count = Column(Integer, nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)

    # Relationship with agents
    agents = relationship("Agent", secondary=agent_knowledge, back_populates="knowledge_bases")
