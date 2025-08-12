from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, text, distinct, case
from sqlalchemy.orm import selectinload
from app.db.models.dashboard_analytics import ExportHistory
from app.db.models.analytics import ChatMetrics, AgentPerformanceMetrics
from app.db.models.performance import SystemMetrics, APIMetrics
from app.db.models.agent import Agent
from app.db.models.user import User
from app.db.models.chat import Conversation, ChatMessage
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import json
import csv
import io
from reportlab.lib.pagesizes import letter # type: ignore
from reportlab.lib import colors # type: ignore
from reportlab.lib.styles import getSampleStyleSheet # type: ignore
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer # type: ignore
from fastapi import HTTPException, status
from app.core.config import settings

logger = logging.getLogger(__name__)

class DashboardService:
    
    @staticmethod
    async def get_dashboard_overview(
        db: AsyncSession,
        organization_id: int,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Get comprehensive dashboard overview"""
        try:
            # Set default date range (last 30 days)
            if not start_date:
                start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.utcnow().strftime("%Y-%m-%d")
            
            # Get usage analytics
            usage_data = await DashboardService._get_usage_analytics(
                db, organization_id, start_date, end_date, filters
            )
            
            # Get chat metrics
            chat_data = await DashboardService._get_chat_analytics(
                db, organization_id, start_date, end_date, filters
            )
            
            # Get performance metrics
            performance_data = await DashboardService._get_performance_analytics(
                db, organization_id, start_date, end_date, filters
            )
            
            # Get trends data
            trends_data = await DashboardService._get_trends_data(
                db, organization_id, start_date, end_date
            )
            
            return {
                "period": {"start_date": start_date, "end_date": end_date},
                "organization_id": organization_id,
                "usage_analytics": usage_data,
                "chat_metrics": chat_data,
                "performance_monitoring": performance_data,
                "trends": trends_data,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard overview: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch dashboard data")
    
    @staticmethod
    async def _get_usage_analytics(
        db: AsyncSession, 
        organization_id: int, 
        start_date: str, 
        end_date: str, 
        filters: Optional[Dict]
    ) -> Dict[str, Any]:
        """Get usage analytics data"""
        try:
            # Active agents count
            active_agents = await db.execute(
                select(func.count(distinct(Agent.id)))
                .where(Agent.organization_id == organization_id)
            )
            
            # Active users count (users with conversations in period)
            active_users = await db.execute(
                select(func.count(distinct(ChatMetrics.user_id)))
                .where(
                    and_(
                        ChatMetrics.organization_id == organization_id,
                        ChatMetrics.date_bucket >= start_date,
                        ChatMetrics.date_bucket <= end_date
                    )
                )
            )
            
            # Total conversations
            total_conversations = await db.execute(
                select(func.count(distinct(ChatMetrics.conversation_id)))
                .where(
                    and_(
                        ChatMetrics.organization_id == organization_id,
                        ChatMetrics.date_bucket >= start_date,
                        ChatMetrics.date_bucket <= end_date
                    )
                )
            )
            
            # Knowledge bases usage
            kb_usage = await db.execute(
                select(func.sum(ChatMetrics.knowledge_base_hits))
                .where(
                    and_(
                        ChatMetrics.organization_id == organization_id,
                        ChatMetrics.date_bucket >= start_date,
                        ChatMetrics.date_bucket <= end_date
                    )
                )
            )
            
            # Daily usage trends
            daily_usage = await db.execute(
                select(
                    ChatMetrics.date_bucket,
                    func.count(ChatMetrics.id).label('daily_interactions'),
                    func.count(distinct(ChatMetrics.user_id)).label('daily_users'),
                    func.count(distinct(ChatMetrics.conversation_id)).label('daily_conversations')
                ).where(
                    and_(
                        ChatMetrics.organization_id == organization_id,
                        ChatMetrics.date_bucket >= start_date,
                        ChatMetrics.date_bucket <= end_date
                    )
                ).group_by(ChatMetrics.date_bucket).order_by(ChatMetrics.date_bucket)
            )
            
            return {
                "summary": {
                    "active_agents": active_agents.scalar() or 0,
                    "active_users": active_users.scalar() or 0,
                    "total_conversations": total_conversations.scalar() or 0,
                    "knowledge_base_hits": kb_usage.scalar() or 0
                },
                "daily_trends": [
                    {
                        "date": row.date_bucket,
                        "interactions": row.daily_interactions,
                        "users": row.daily_users,
                        "conversations": row.daily_conversations
                    }
                    for row in daily_usage
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting usage analytics: {str(e)}")
            return {"summary": {}, "daily_trends": []}
    
    @staticmethod
    async def _get_chat_analytics(
        db: AsyncSession, 
        organization_id: int, 
        start_date: str, 
        end_date: str, 
        filters: Optional[Dict]
    ) -> Dict[str, Any]:
        """Get chat analytics data"""
        try:
            # Chat volume metrics
            chat_volume = await db.execute(
                select(
                    func.count(ChatMetrics.id).label('total_messages'),
                    func.avg(ChatMetrics.response_time_ms).label('avg_response_time'),
                    func.avg(ChatMetrics.message_length).label('avg_message_length'),
                    func.sum(ChatMetrics.tokens_used).label('total_tokens'),
                    func.sum(ChatMetrics.cost).label('total_cost')
                ).where(
                    and_(
                        ChatMetrics.organization_id == organization_id,
                        ChatMetrics.date_bucket >= start_date,
                        ChatMetrics.date_bucket <= end_date
                    )
                )
            )
            
            volume_data = chat_volume.first()
            
            # Top performing agents
            top_agents = await db.execute(
                select(
                    Agent.id,
                    Agent.name,
                    func.count(ChatMetrics.id).label('message_count'),
                    func.avg(ChatMetrics.response_time_ms).label('avg_response_time'),
                    func.sum(ChatMetrics.cost).label('total_cost')
                ).select_from(
                    Agent.__table__.join(ChatMetrics, Agent.id == ChatMetrics.agent_id)
                ).where(
                    and_(
                        Agent.organization_id == organization_id,
                        ChatMetrics.date_bucket >= start_date,
                        ChatMetrics.date_bucket <= end_date
                    )
                ).group_by(Agent.id, Agent.name)
                .order_by(desc('message_count')).limit(10)
            )
            
            # Hourly usage patterns
            hourly_patterns = await db.execute(
                select(
                    ChatMetrics.hour_bucket,
                    func.count(ChatMetrics.id).label('message_count'),
                    func.avg(ChatMetrics.response_time_ms).label('avg_response_time')
                ).where(
                    and_(
                        ChatMetrics.organization_id == organization_id,
                        ChatMetrics.date_bucket >= start_date,
                        ChatMetrics.date_bucket <= end_date
                    )
                ).group_by(ChatMetrics.hour_bucket).order_by(ChatMetrics.hour_bucket)
            )
            
            return {
                "summary": {
                    "total_messages": volume_data.total_messages or 0,
                    "avg_response_time_ms": round(volume_data.avg_response_time or 0, 2),
                    "avg_message_length": round(volume_data.avg_message_length or 0, 1),
                    "total_tokens_used": volume_data.total_tokens or 0,
                    "total_cost_usd": round(volume_data.total_cost or 0, 4)
                },
                "top_agents": [
                    {
                        "agent_id": row.id,
                        "agent_name": row.name,
                        "message_count": row.message_count,
                        "avg_response_time_ms": round(row.avg_response_time or 0, 2),
                        "total_cost_usd": round(row.total_cost or 0, 4)
                    }
                    for row in top_agents
                ],
                "hourly_patterns": [
                    {
                        "hour": row.hour_bucket,
                        "message_count": row.message_count,
                        "avg_response_time_ms": round(row.avg_response_time or 0, 2)
                    }
                    for row in hourly_patterns
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting chat analytics: {str(e)}")
            return {"summary": {}, "top_agents": [], "hourly_patterns": []}
    
    @staticmethod
    async def _get_performance_analytics(
        db: AsyncSession, 
        organization_id: int, 
        start_date: str, 
        end_date: str, 
        filters: Optional[Dict]
    ) -> Dict[str, Any]:
        """Get performance analytics data"""
        try:
            cutoff_time = datetime.strptime(start_date, "%Y-%m-%d")
            
            # System performance metrics
            system_metrics = await db.execute(
                select(
                    func.avg(SystemMetrics.response_time_ms).label('avg_response_time'),
                    func.avg(SystemMetrics.cpu_usage_percent).label('avg_cpu_usage'),
                    func.avg(SystemMetrics.memory_usage_percent).label('avg_memory_usage'),
                    func.avg(SystemMetrics.disk_usage_percent).label('avg_disk_usage')
                ).where(SystemMetrics.timestamp >= cutoff_time)
            )
            
            system_data = system_metrics.first()
            
            # API error rates - Fixed the case() function usage
            api_errors = await db.execute(
                select(
                    func.count(APIMetrics.id).label('total_requests'),
                    func.sum(
                        case(
                            (APIMetrics.is_error == True, 1),
                            else_=0
                        )
                    ).label('error_count')
                ).where(APIMetrics.timestamp >= cutoff_time)
            )
            
            api_data = api_errors.first()
            error_rate = (api_data.error_count / api_data.total_requests * 100) if api_data.total_requests > 0 else 0
            
            # Top slow endpoints
            slow_endpoints = await db.execute(
                select(
                    APIMetrics.endpoint,
                    func.avg(APIMetrics.response_time_ms).label('avg_response_time'),
                    func.count(APIMetrics.id).label('request_count')
                ).where(APIMetrics.timestamp >= cutoff_time)
                .group_by(APIMetrics.endpoint)
                .order_by(desc('avg_response_time')).limit(10)
            )
            
            return {
                "summary": {
                    "avg_response_time_ms": round(system_data.avg_response_time or 0, 2),
                    "avg_cpu_usage_percent": round(system_data.avg_cpu_usage or 0, 2),
                    "avg_memory_usage_percent": round(system_data.avg_memory_usage or 0, 2),
                    "avg_disk_usage_percent": round(system_data.avg_disk_usage or 0, 2),
                    "error_rate_percent": round(error_rate, 2),
                    "total_requests": api_data.total_requests or 0
                },
                "slow_endpoints": [
                    {
                        "endpoint": row.endpoint,
                        "avg_response_time_ms": round(row.avg_response_time or 0, 2),
                        "request_count": row.request_count
                    }
                    for row in slow_endpoints
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting performance analytics: {str(e)}")
            return {"summary": {}, "slow_endpoints": []}
    
    @staticmethod
    async def _get_trends_data(
        db: AsyncSession, 
        organization_id: int, 
        start_date: str, 
        end_date: str
    ) -> Dict[str, Any]:
        """Get trends data for charts"""
        try:
            # Daily message volume trend
            message_trends = await db.execute(
                select(
                    ChatMetrics.date_bucket,
                    func.count(ChatMetrics.id).label('message_count')
                ).where(
                    and_(
                        ChatMetrics.organization_id == organization_id,
                        ChatMetrics.date_bucket >= start_date,
                        ChatMetrics.date_bucket <= end_date
                    )
                ).group_by(ChatMetrics.date_bucket).order_by(ChatMetrics.date_bucket)
            )
            
            # Response time trends
            response_time_trends = await db.execute(
                select(
                    ChatMetrics.date_bucket,
                    func.avg(ChatMetrics.response_time_ms).label('avg_response_time')
                ).where(
                    and_(
                        ChatMetrics.organization_id == organization_id,
                        ChatMetrics.date_bucket >= start_date,
                        ChatMetrics.date_bucket <= end_date
                    )
                ).group_by(ChatMetrics.date_bucket).order_by(ChatMetrics.date_bucket)
            )
            
            # Cost trends
            cost_trends = await db.execute(
                select(
                    ChatMetrics.date_bucket,
                    func.sum(ChatMetrics.cost).label('daily_cost')
                ).where(
                    and_(
                        ChatMetrics.organization_id == organization_id,
                        ChatMetrics.date_bucket >= start_date,
                        ChatMetrics.date_bucket <= end_date
                    )
                ).group_by(ChatMetrics.date_bucket).order_by(ChatMetrics.date_bucket)
            )
            
            return {
                "message_volume": [
                    {"date": row.date_bucket, "count": row.message_count}
                    for row in message_trends
                ],
                "response_time": [
                    {"date": row.date_bucket, "avg_ms": round(row.avg_response_time or 0, 2)}
                    for row in response_time_trends
                ],
                "cost": [
                    {"date": row.date_bucket, "cost_usd": round(row.daily_cost or 0, 4)}
                    for row in cost_trends
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting trends data: {str(e)}")
            return {"message_volume": [], "response_time": [], "cost": []}
    
    @staticmethod
    async def export_dashboard_report(
        db: AsyncSession,
        organization_id: int,
        user_id: str,
        export_type: str,
        start_date: str,
        end_date: str,
        filters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Export dashboard data in specified format"""
        try:
            # Get dashboard data
            dashboard_data = await DashboardService.get_dashboard_overview(
                db, organization_id, user_id, start_date, end_date, filters
            )
            
            # Create export record
            export_record = ExportHistory(
                export_type=export_type,
                report_name=f"Dashboard Report {start_date} to {end_date}",
                date_range_start=start_date,
                date_range_end=end_date,
                filters_applied=filters or {},
                organization_id=organization_id,
                exported_by=user_id,
                export_status='pending'
            )
            
            db.add(export_record)
            await db.flush()
            
            if export_type == 'csv':
                export_data = DashboardService._export_to_csv(dashboard_data)
            elif export_type == 'pdf':
                export_data = DashboardService._export_to_pdf(dashboard_data)
            elif export_type == 'json':
                export_data = json.dumps(dashboard_data, indent=2)
            else:
                raise ValueError(f"Unsupported export type: {export_type}")
            
            # Update export record
            export_record.export_status = 'completed'
            export_record.completed_at = datetime.utcnow()
            export_record.file_size_bytes = len(export_data.encode()) if isinstance(export_data, str) else len(export_data)
            
            await db.commit()
            
            return {
                "export_id": export_record.id,
                "export_type": export_type,
                "data": export_data,
                "file_size_bytes": export_record.file_size_bytes,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Error exporting dashboard report: {str(e)}")
            if 'export_record' in locals():
                export_record.export_status = 'failed'
                await db.commit()
            raise HTTPException(status_code=500, detail="Failed to export report")
    
    @staticmethod
    def _export_to_csv(dashboard_data: Dict) -> str:
        """Convert dashboard data to CSV format"""
        output = io.StringIO()
        
        # Summary data
        writer = csv.writer(output)
        writer.writerow(['Dashboard Report Summary'])
        writer.writerow(['Period', f"{dashboard_data['period']['start_date']} to {dashboard_data['period']['end_date']}"])
        writer.writerow([])
        
        # Usage Analytics
        writer.writerow(['Usage Analytics'])
        usage = dashboard_data.get('usage_analytics', {}).get('summary', {})
        for key, value in usage.items():
            writer.writerow([key.replace('_', ' ').title(), value])
        writer.writerow([])
        
        # Chat Metrics
        writer.writerow(['Chat Metrics'])
        chat = dashboard_data.get('chat_metrics', {}).get('summary', {})
        for key, value in chat.items():
            writer.writerow([key.replace('_', ' ').title(), value])
        writer.writerow([])
        
        # Performance Metrics
        writer.writerow(['Performance Metrics'])
        performance = dashboard_data.get('performance_monitoring', {}).get('summary', {})
        for key, value in performance.items():
            writer.writerow([key.replace('_', ' ').title(), value])
        
        return output.getvalue()
    
    @staticmethod
    def _export_to_pdf(dashboard_data: Dict) -> bytes:
        """Convert dashboard data to PDF format"""
        # This is a simplified PDF export - you might want to enhance with charts
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        story.append(Paragraph("Dashboard Report", styles['Title']))
        story.append(Spacer(1, 20))
        
        # Period
        period = dashboard_data.get('period', {})
        story.append(Paragraph(f"Period: {period.get('start_date')} to {period.get('end_date')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Usage Analytics
        story.append(Paragraph("Usage Analytics", styles['Heading2']))
        usage_data = []
        usage = dashboard_data.get('usage_analytics', {}).get('summary', {})
        for key, value in usage.items():
            usage_data.append([key.replace('_', ' ').title(), str(value)])
        
        if usage_data:
            usage_table = Table(usage_data)
            usage_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(usage_table)
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()