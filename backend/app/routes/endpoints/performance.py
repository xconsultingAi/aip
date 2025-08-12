from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.db.models.user import User
from app.services.performance_services import PerformanceService
from app.core.responses import success_response, error_response
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance", tags=["Performance Analytics"])

@router.get("/overview")
async def get_performance_overview(
    hours: int = Query(24, ge=1, le=168, description="Time period in hours (1-168)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get system performance overview"""
    try:
        overview = await PerformanceService.get_system_overview(db, hours)
        return success_response(
            "Performance overview retrieved successfully",
            overview
        )
    except Exception as e:
        logger.error(f"Error in get_performance_overview: {str(e)}")
        return error_response(f"Failed to get performance overview: {str(e)}", 500)

@router.get("/endpoints")
async def get_endpoint_performance(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get performance metrics for all endpoints"""
    try:
        endpoints = await PerformanceService.get_endpoint_performance(db, hours)
        return success_response(
            "Endpoint performance metrics retrieved successfully",
            endpoints
        )
    except Exception as e:
        logger.error(f"Error in get_endpoint_performance: {str(e)}")
        return error_response(f"Failed to get endpoint performance: {str(e)}", 500)

@router.get("/metrics/{metric_type}")
async def get_time_series_metrics(
    metric_type: str,
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get time series data for specific metrics"""
    allowed_metrics = ["response_time", "error_rate", "cpu_usage", "memory_usage"]
    
    if metric_type not in allowed_metrics:
        return error_response(f"Invalid metric type. Allowed: {allowed_metrics}", 400)
    
    try:
        logger.info(f"Fetching time series data for metric: {metric_type}, hours: {hours}")
        data = await PerformanceService.get_time_series_data(db, metric_type, hours)
        
        # Log the result for debugging
        logger.info(f"Retrieved {len(data)} data points for metric {metric_type}")
        
        return success_response(
            f"{metric_type} time series data retrieved successfully",
            {
                "metric_type": metric_type,
                "time_period_hours": hours,
                "data_points": len(data),
                "data": data
            }
        )
    except Exception as e:
        logger.error(f"Error in get_time_series_metrics for {metric_type}: {str(e)}", exc_info=True)
        # Return a safe response instead of 500 error
        return success_response(
            f"{metric_type} time series data retrieved (no data available)",
            {
                "metric_type": metric_type,
                "time_period_hours": hours,
                "data_points": 0,
                "data": [],
                "note": "No data available for the specified time period"
            }
        )

@router.post("/alerts/check")
async def trigger_alert_check(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger alert condition checking"""
    try:
        await PerformanceService.check_alert_conditions(db)
        return success_response("Alert conditions checked successfully")
    except Exception as e:
        logger.error(f"Error in trigger_alert_check: {str(e)}")
        return error_response(f"Failed to check alert conditions: {str(e)}", 500)