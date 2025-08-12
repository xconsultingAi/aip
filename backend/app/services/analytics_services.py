from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, text
from sqlalchemy.orm import selectinload
from app.db.models.analytics import ChatMetrics, AgentPerformanceMetrics
from app.db.models.agent import Agent
from app.db.models.chat import Conversation, ChatMessage
from app.db.models.user import User
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from app.core.config import settings
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class AnalyticsService:
    
    @staticmethod
    async def record_chat_metric(
        db: AsyncSession,
        conversation_id: int,
        agent_id: int,
        user_id: str,
        organization_id: int,
        response_time_ms: float,
        message_length: int,
        tokens_used: int = 0,
        cost: float = 0.0,
        knowledge_base_hits: int = 0,
        model_used: str = None
    ):
        """Record individual chat interaction metrics"""
        try:
            now = datetime.utcnow()
            
            metric = ChatMetrics(
                conversation_id=conversation_id,
                agent_id=agent_id,
                user_id=user_id,
                organization_id=organization_id,
                response_time_ms=response_time_ms,
                message_length=message_length,
                tokens_used=tokens_used,
                cost=cost,
                knowledge_base_hits=knowledge_base_hits,
                model_used=model_used or settings.FALLBACK_MODEL,
                date_bucket=now.strftime("%Y-%m-%d"),
                hour_bucket=now.hour
            )
            
            db.add(metric)
            await db.commit()
            logger.info(f"Chat metric recorded for agent {agent_id}")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to record chat metric: {str(e)}")

    @staticmethod
    async def get_agent_performance_summary(
        db: AsyncSession,
        agent_id: int,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive agent performance metrics"""
        try:
            # Default to last 30 days if no dates provided
            if not start_date:
                start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.utcnow().strftime("%Y-%m-%d")
            
            # Verify agent ownership
            agent_result = await db.execute(
                select(Agent).where(Agent.id == agent_id, Agent.user_id == user_id)
            )
            agent = agent_result.scalar_one_or_none()
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            
            # Get aggregated metrics
            metrics_result = await db.execute(
                select(
                    func.count(ChatMetrics.id).label('total_interactions'),
                    func.avg(ChatMetrics.response_time_ms).label('avg_response_time'),
                    func.min(ChatMetrics.response_time_ms).label('min_response_time'),
                    func.max(ChatMetrics.response_time_ms).label('max_response_time'),
                    func.sum(ChatMetrics.tokens_used).label('total_tokens'),
                    func.sum(ChatMetrics.cost).label('total_cost'),
                    func.avg(ChatMetrics.message_length).label('avg_message_length'),
                    func.sum(ChatMetrics.knowledge_base_hits).label('total_kb_hits')
                ).where(
                    and_(
                        ChatMetrics.agent_id == agent_id,
                        ChatMetrics.date_bucket >= start_date,
                        ChatMetrics.date_bucket <= end_date
                    )
                )
            )
            metrics = metrics_result.first()
            
            # Get conversation metrics
            conv_result = await db.execute(
                select(
                    func.count(func.distinct(ChatMetrics.conversation_id)).label('total_conversations'),
                    func.avg(ChatMetrics.message_count).label('avg_messages_per_conversation')
                ).where(
                    and_(
                        ChatMetrics.agent_id == agent_id,
                        ChatMetrics.date_bucket >= start_date,
                        ChatMetrics.date_bucket <= end_date
                    )
                )
            )
            conv_metrics = conv_result.first()
            
            # Get daily trends
            daily_trends = await db.execute(
                select(
                    ChatMetrics.date_bucket,
                    func.count(ChatMetrics.id).label('daily_messages'),
                    func.avg(ChatMetrics.response_time_ms).label('daily_avg_response_time'),
                    func.sum(ChatMetrics.cost).label('daily_cost')
                ).where(
                    and_(
                        ChatMetrics.agent_id == agent_id,
                        ChatMetrics.date_bucket >= start_date,
                        ChatMetrics.date_bucket <= end_date
                    )
                ).group_by(ChatMetrics.date_bucket).order_by(ChatMetrics.date_bucket)
            )
            
            return {
                "agent_id": agent_id,
                "agent_name": agent.name,
                "period": {"start_date": start_date, "end_date": end_date},
                "summary": {
                    "total_interactions": metrics.total_interactions or 0,
                    "total_conversations": conv_metrics.total_conversations or 0,
                    "avg_response_time_ms": round(metrics.avg_response_time or 0, 2),
                    "min_response_time_ms": metrics.min_response_time or 0,
                    "max_response_time_ms": metrics.max_response_time or 0,
                    "total_tokens_used": metrics.total_tokens or 0,
                    "total_cost_usd": round(metrics.total_cost or 0, 4),
                    "avg_message_length": round(metrics.avg_message_length or 0, 1),
                    "avg_messages_per_conversation": round(conv_metrics.avg_messages_per_conversation or 0, 1),
                    "knowledge_base_usage_rate": round(
                        (metrics.total_kb_hits or 0) / max(metrics.total_interactions or 1, 1) * 100, 1
                    )
                },
                "daily_trends": [
                    {
                        "date": row.date_bucket,
                        "messages": row.daily_messages,
                        "avg_response_time_ms": round(row.daily_avg_response_time or 0, 2),
                        "cost_usd": round(row.daily_cost or 0, 4)
                    }
                    for row in daily_trends
                ]
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting agent performance summary: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch performance metrics")

    @staticmethod
    async def get_organization_analytics(
        db: AsyncSession,
        organization_id: int,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get organization-wide analytics dashboard"""
        try:
            if not start_date:
                start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.utcnow().strftime("%Y-%m-%d")
            
            # Get top performing agents
            top_agents_result = await db.execute(
                select(
                    Agent.id,
                    Agent.name,
                    func.count(ChatMetrics.id).label('total_interactions'),
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
                ).group_by(Agent.id, Agent.name).order_by(desc('total_interactions')).limit(10)
            )
            
            # Get hourly usage patterns
            hourly_usage = await db.execute(
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
            
            # Get overall organization metrics
            org_summary = await db.execute(
                select(
                    func.count(ChatMetrics.id).label('total_messages'),
                    func.count(func.distinct(ChatMetrics.conversation_id)).label('total_conversations'),
                    func.count(func.distinct(ChatMetrics.agent_id)).label('active_agents'),
                    func.avg(ChatMetrics.response_time_ms).label('avg_response_time'),
                    func.sum(ChatMetrics.cost).label('total_cost'),
                    func.sum(ChatMetrics.tokens_used).label('total_tokens')
                ).where(
                    and_(
                        ChatMetrics.organization_id == organization_id,
                        ChatMetrics.date_bucket >= start_date,
                        ChatMetrics.date_bucket <= end_date
                    )
                )
            )
            org_metrics = org_summary.first()
            
            return {
                "organization_id": organization_id,
                "period": {"start_date": start_date, "end_date": end_date},
                "summary": {
                    "total_messages": org_metrics.total_messages or 0,
                    "total_conversations": org_metrics.total_conversations or 0,
                    "active_agents": org_metrics.active_agents or 0,
                    "avg_response_time_ms": round(org_metrics.avg_response_time or 0, 2),
                    "total_cost_usd": round(org_metrics.total_cost or 0, 4),
                    "total_tokens_used": org_metrics.total_tokens or 0
                },
                "top_agents": [
                    {
                        "agent_id": row.id,
                        "agent_name": row.name,
                        "total_interactions": row.total_interactions,
                        "avg_response_time_ms": round(row.avg_response_time or 0, 2),
                        "total_cost_usd": round(row.total_cost or 0, 4)
                    }
                    for row in top_agents_result
                ],
                "hourly_usage": [
                    {
                        "hour": row.hour_bucket,
                        "message_count": row.message_count,
                        "avg_response_time_ms": round(row.avg_response_time or 0, 2)
                    }
                    for row in hourly_usage
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting organization analytics: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch organization analytics")

    @staticmethod
    async def export_chat_metrics(
        db: AsyncSession,
        organization_id: int,
        user_id: str,
        start_date: str,
        end_date: str,
        format: str = "csv"
    ) -> List[Dict[str, Any]]:
        """Export chat metrics for external analysis"""
        try:
            result = await db.execute(
                select(
                    ChatMetrics.created_at,
                    ChatMetrics.agent_id,
                    Agent.name.label('agent_name'),
                    ChatMetrics.response_time_ms,
                    ChatMetrics.message_length,
                    ChatMetrics.tokens_used,
                    ChatMetrics.cost,
                    ChatMetrics.knowledge_base_hits,
                    ChatMetrics.model_used
                ).select_from(
                    ChatMetrics.__table__.join(Agent, ChatMetrics.agent_id == Agent.id)
                ).where(
                    and_(
                        ChatMetrics.organization_id == organization_id,
                        ChatMetrics.date_bucket >= start_date,
                        ChatMetrics.date_bucket <= end_date
                    )
                ).order_by(ChatMetrics.created_at.desc())
            )
            
            return [
                {
                    "timestamp": row.created_at.isoformat(),
                    "agent_id": row.agent_id,
                    "agent_name": row.agent_name,
                    "response_time_ms": row.response_time_ms,
                    "message_length": row.message_length,
                    "tokens_used": row.tokens_used,
                    "cost_usd": row.cost,
                    "knowledge_base_hits": row.knowledge_base_hits,
                    "model_used": row.model_used
                }
                for row in result
            ]
            
        except Exception as e:
            logger.error(f"Error exporting chat metrics: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to export metrics")
