from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON, Index, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class SystemMetrics(Base):
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    
    # Core metrics
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    response_time_ms = Column(Float, nullable=False)
    cpu_usage_percent = Column(Float, default=0.0)
    memory_usage_percent = Column(Float, default=0.0)
    disk_usage_percent = Column(Float, default=0.0)
    
    # API specific metrics
    endpoint = Column(String(200))
    method = Column(String(10))
    status_code = Column(Integer)
    error_message = Column(String(500))
    
    # Metadata
    date_bucket = Column(String(10))  # YYYY-MM-DD
    hour_bucket = Column(Integer)     # 0-23
    
    __table_args__ = (
        Index('ix_system_metrics_timestamp', 'timestamp'),
        Index('ix_system_metrics_endpoint', 'endpoint'),
        Index('ix_system_metrics_date_hour', 'date_bucket', 'hour_bucket'),
    )

class APIMetrics(Base):
    __tablename__ = "api_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Request info
    endpoint = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Float, nullable=False)
    
    # Request details
    user_id = Column(String, ForeignKey("users.user_id"))
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    request_size_bytes = Column(Integer, default=0)
    response_size_bytes = Column(Integer, default=0)
    
    # Error tracking
    is_error = Column(Boolean, default=False)
    error_type = Column(String(100))
    error_message = Column(String(500))
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    date_bucket = Column(String(10))
    hour_bucket = Column(Integer)
    
    __table_args__ = (
        Index('ix_api_metrics_endpoint_status', 'endpoint', 'status_code'),
        Index('ix_api_metrics_timestamp', 'timestamp'),
        Index('ix_api_metrics_errors', 'is_error', 'timestamp'),
    )

class AlertRules(Base):
    __tablename__ = "alert_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    
    # Rule definition
    metric_type = Column(String(50), nullable=False)  # 'response_time', 'error_rate', 'uptime'
    threshold_value = Column(Float, nullable=False)
    comparison_operator = Column(String(10), nullable=False)  # '>', '<', '>=', '<='
    time_window_minutes = Column(Integer, default=5)
    
    # Alert settings
    is_active = Column(Boolean, default=True)
    severity = Column(String(20), default='medium')  # 'low', 'medium', 'high', 'critical'
    notification_channels = Column(JSON, default=[])
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SystemAlerts(Base):
    __tablename__ = "system_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=False)
    
    # Alert details
    title = Column(String(200), nullable=False)
    message = Column(String(1000), nullable=False)
    severity = Column(String(20), nullable=False)
    status = Column(String(20), default='open')  # 'open', 'acknowledged', 'resolved'
    
    # Metrics that triggered alert
    trigger_value = Column(Float)
    threshold_value = Column(Float)
    affected_endpoint = Column(String(200))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    
    # Relationships
    alert_rule = relationship("AlertRules")