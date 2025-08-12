from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class ChatMetrics(Base):
    __tablename__ = "chat_metrics"

    id = Column(Integer, primary_key=True, index=True)
    
    # Core metrics
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    # Performance metrics
    response_time_ms = Column(Float, nullable=False)  # Agent response time in milliseconds
    message_length = Column(Integer, nullable=False)  # Character count of user message
    tokens_used = Column(Integer, default=0)  # LLM tokens consumed
    cost = Column(Float, default=0.0)  # Processing cost
    
    # Session metrics
    session_duration_seconds = Column(Integer)  # Total conversation duration
    message_count = Column(Integer, default=1)  # Messages in this conversation
    
    # Quality indicators
    knowledge_base_hits = Column(Integer, default=0)  # RAG context retrievals
    model_used = Column(String(50))  # LLM model identifier
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    date_bucket = Column(String(10))  # YYYY-MM-DD for aggregation
    hour_bucket = Column(Integer)  # 0-23 for hourly analysis
    
    # Relationships
    conversation = relationship("Conversation")
    agent = relationship("Agent")
    user = relationship("User")
    organization = relationship("Organization")
    
    __table_args__ = (
        Index('ix_metrics_agent_date', 'agent_id', 'date_bucket'),
        Index('ix_metrics_org_date', 'organization_id', 'date_bucket'),
        Index('ix_metrics_user_date', 'user_id', 'date_bucket'),
        Index('ix_metrics_response_time', 'response_time_ms'),
    )

class AgentPerformanceMetrics(Base):
    __tablename__ = "agent_performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    # Aggregated metrics (daily)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    total_conversations = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    avg_response_time_ms = Column(Float, default=0.0)
    total_tokens_used = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    
    # Performance indicators
    avg_session_duration = Column(Float, default=0.0)
    avg_messages_per_conversation = Column(Float, default=0.0)
    knowledge_base_usage_rate = Column(Float, default=0.0)  # Percentage of messages using KB
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    agent = relationship("Agent")
    organization = relationship("Organization")
    
    __table_args__ = (
        Index('ix_agent_metrics_date', 'agent_id', 'date'),
        Index('ix_agent_metrics_org', 'organization_id', 'date'),
    )