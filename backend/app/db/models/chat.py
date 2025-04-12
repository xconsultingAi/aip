from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base

#SH: This is database model used for Migrations & CRUD operations

# SH: TODO - Implement real-time streaming of chat messages
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    #SH: user or agent
    sender = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    delivered = Column(Boolean, default=False)
    read = Column(Boolean, default=False)
    user_id = Column(String, ForeignKey("users.user_id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))