from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
from datetime import datetime
from app.db.database import Base

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255))
    content_type = Column(String(50))
    organization_id = Column(Integer, ForeignKey("organizations.id"))  
    uploaded_at = Column(DateTime, default=datetime.utcnow)  

#SH: Relationship between Agent & KnowledgeBase
agent_knowledge = Table(
    'agent_knowledge',
    Base.metadata,
    Column('agent_id', Integer, ForeignKey('agents.id')),  
    Column('knowledge_id', Integer, ForeignKey('knowledge_bases.id'))
)
