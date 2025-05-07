from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base
from sqlalchemy.orm import relationship

# MJ: This is the database model used for Migrations & CRUD operations
class WidgetSession(Base):
    __tablename__ = "widget_sessions"
    
    id = Column(Integer, primary_key=True)
    visitor_id = Column(String(255), unique=True, nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active = Column(DateTime(timezone=True), onupdate=func.now())
    message_count = Column(Integer, default=0)
    status = Column(String(20), default='active')
    
    # Relationship with Agent
    agent = relationship("Agent", back_populates="widget_sessions")
    