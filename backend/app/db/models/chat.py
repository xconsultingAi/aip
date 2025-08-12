from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base
from sqlalchemy.orm import validates

#SH: This is database model used for Migrations & CRUD operations
class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user_id = Column(String, ForeignKey("users.user_id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))

    #SH: Relationships
    user = relationship("User", back_populates="conversations")
    agent = relationship("Agent", back_populates="conversations")
    messages = relationship("ChatMessage", back_populates="conversation", order_by="ChatMessage.sequence_id")
    organization_id = Column(Integer, ForeignKey("organizations.id")) 
       
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)

    #SH: Core message info
    sequence_id = Column(Integer, nullable=False, server_default="1")
    prev_message_hash = Column(String(64))

    content = Column(String, nullable=False)
    #SH: user or agent
    sender = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Status flags
    delivered = Column(Boolean, default=False)
    read = Column(Boolean, default=False)   

    #SH: Foreign keys / relations
    user_id = Column(String, ForeignKey("users.user_id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    
    # Add these relationship definitions to the ChatMessage class
    user = relationship("User", back_populates="chat_messages")
    agent = relationship("Agent", back_populates="chat_messages")
    conversation = relationship("Conversation", back_populates="messages")
    
    # SH: Sequence validation to ensure positive integers
    @validates('sequence_id')
    def validate_sequence(self, key, value):
        if value < 1:
            raise ValueError("Sequence ID must be positive integer")
        return value

    __table_args__ = (
        Index('ix_chatmessages_user_agent', 'user_id', 'agent_id'),
        Index('ix_chatmessages_timestamp', 'timestamp'),
        Index('ix_conversation_sequence', 'conversation_id', 'sequence_id', unique=True),
    )