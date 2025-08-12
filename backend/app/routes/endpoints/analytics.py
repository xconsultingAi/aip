from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.db.models.user import User 
from app.services.analytics_services import AnalyticsService
from app.core.responses import success_response, error_response
from typing import Optional
import logging
from datetime import datetime

router = APIRouter(tags=["Analytics"])
logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)
@router.get("/agent/{agent_id}/performance")
async def get_agent_performance(
    agent_id: int,
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive performance metrics for a specific agent"""
    try:
        performance_data = await AnalyticsService.get_agent_performance_summary(
            db, agent_id, current_user.user_id, start_date, end_date
        )
        return success_response(
            "Agent performance metrics retrieved successfully",
            performance_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching agent performance: {str(e)}")
        return error_response(
            "Failed to retrieve agent performance metrics",
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/organization/dashboard")
async def get_organization_dashboard(
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get organization-wide analytics dashboard"""
    try:
        if not current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not associated with an organization"
            )
        
        dashboard_data = await AnalyticsService.get_organization_analytics(
            db, current_user.organization_id, current_user.user_id, start_date, end_date
        )
        return success_response(
            "Organization analytics retrieved successfully",
            dashboard_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching organization dashboard: {str(e)}")
        return error_response(
            "Failed to retrieve organization analytics",
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/export")
async def export_metrics(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    format: str = Query("csv", description="Export format (csv, json)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export chat metrics for external analysis"""
    try:
        if not current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not associated with an organization"
            )
        
        # Validate date format
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        export_data = await AnalyticsService.export_chat_metrics(
            db, current_user.organization_id, current_user.user_id, 
            start_date, end_date, format
        )
        
        return success_response(
            f"Metrics exported successfully ({len(export_data)} records)",
            {"data": export_data, "format": format, "record_count": len(export_data)}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting metrics: {str(e)}")
        return error_response(
            "Failed to export metrics",
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )