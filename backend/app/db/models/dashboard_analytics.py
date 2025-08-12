from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON, Index, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class DashboardMetrics(Base):
    __tablename__ = "dashboard_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Metric identification
    metric_type = Column(String(50), nullable=False)  # 'usage', 'chat', 'performance'
    metric_name = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20))  # 'count', 'ms', 'percent', 'usd'
    
    # Context data
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    user_id = Column(String, ForeignKey("users.user_id"))
    
    # Time buckets for aggregation
    date_bucket = Column(String(10))  # YYYY-MM-DD
    hour_bucket = Column(Integer)     # 0-23
    month_bucket = Column(String(7))  # YYYY-MM
    
    # Metadata
    additional_data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_dashboard_metrics_type_date', 'metric_type', 'date_bucket'),
        Index('ix_dashboard_metrics_org_date', 'organization_id', 'date_bucket'),
    )

class ReportTemplates(Base):
    __tablename__ = "report_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    template_type = Column(String(50), nullable=False)  # 'usage', 'performance', 'comprehensive'
    
    # Configuration
    metrics_config = Column(JSON, nullable=False)
    filters_config = Column(JSON, default={})
    chart_config = Column(JSON, default={})
    
    # Access control
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    created_by = Column(String, ForeignKey("users.user_id"))
    is_public = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    creator = relationship("User")
    organization = relationship("Organization")
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "template_type": self.template_type,
            "metrics_config": self.metrics_config,
            "filters_config": self.filters_config,
            "chart_config": self.chart_config,
            "organization_id": self.organization_id,
            "created_by": self.created_by,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class ExportHistory(Base):
    __tablename__ = "export_history"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Export details
    export_type = Column(String(20), nullable=False)  # 'pdf', 'csv', 'excel'
    report_name = Column(String(200))
    file_path = Column(String(500))
    file_size_bytes = Column(Integer)
    
    # Filters applied
    date_range_start = Column(String(10))
    date_range_end = Column(String(10))
    filters_applied = Column(JSON, default={})
    
    # Metadata
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    exported_by = Column(String, ForeignKey("users.user_id"))
    export_status = Column(String(20), default='pending')  # 'pending', 'completed', 'failed'
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User")
    organization = relationship("Organization")