from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.db.models.user import User
from app.services.dashboard_analytics import DashboardService
from app.core.responses import success_response, error_response
from typing import Optional, Dict, Any
import logging
from datetime import datetime
from fastapi.responses import StreamingResponse
import io
from sqlalchemy import select
from app.db.models.dashboard_analytics import ReportTemplates


router = APIRouter(tags=["Dashboard"])
logger = logging.getLogger(__name__)

@router.get("/overview")
async def get_dashboard_overview(
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    agent_ids: Optional[str] = Query(None, description="Comma-separated agent IDs to filter"),
    metric_types: Optional[str] = Query(None, description="Comma-separated metric types"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive dashboard overview with all metrics"""
    try:
        if not current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not associated with an organization"
            )
        
        # Parse filters
        filters = {}
        if agent_ids:
            filters['agent_ids'] = [int(id.strip()) for id in agent_ids.split(',')]
        if metric_types:
            filters['metric_types'] = [type.strip() for type in metric_types.split(',')]
        
        dashboard_data = await DashboardService.get_dashboard_overview(
            db, current_user.organization_id, current_user.user_id, 
            start_date, end_date, filters
        )
        
        return success_response(
            "Dashboard overview retrieved successfully",
            dashboard_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching dashboard overview: {str(e)}")
        return error_response(
            "Failed to retrieve dashboard overview",
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/filters/options")
async def get_filter_options(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get available filter options for dashboard"""
    try:
        if not current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not associated with an organization"
            )
        
        # Get available agents
        from app.db.repository.agent import get_agents_by_organization
        agents = await get_agents_by_organization(db, current_user.organization_id)
        
        # Get available date ranges
        from sqlalchemy import select, func
        from app.db.models.analytics import ChatMetrics
        
        date_range = await db.execute(
            select(
                func.min(ChatMetrics.date_bucket).label('min_date'),
                func.max(ChatMetrics.date_bucket).label('max_date')
            ).where(ChatMetrics.organization_id == current_user.organization_id)
        )
        dates = date_range.first()
        
        filter_options = {
            "agents": [
                {"id": agent.id, "name": agent.name}
                for agent in agents
            ],
            "date_range": {
                "min_date": dates.min_date if dates.min_date else datetime.now().strftime("%Y-%m-%d"),
                "max_date": dates.max_date if dates.max_date else datetime.now().strftime("%Y-%m-%d")
            },
            "metric_types": [
                "usage", "chat", "performance", "cost", "response_time"
            ],
            "export_formats": [
                {"value": "csv", "label": "CSV"},
                {"value": "pdf", "label": "PDF"},
                {"value": "json", "label": "JSON"}
            ]
        }
        
        return success_response(
            "Filter options retrieved successfully",
            filter_options
        )
        
    except Exception as e:
        logger.error(f"Error fetching filter options: {str(e)}")
        return error_response(
            "Failed to retrieve filter options",
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/export")
async def export_dashboard_data(
    export_type: str = Query(..., description="Export format (csv, pdf, json)"),
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    agent_ids: Optional[str] = Query(None, description="Comma-separated agent IDs to filter"),
    metric_types: Optional[str] = Query(None, description="Comma-separated metric types"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export dashboard data in specified format"""
    try:
        if not current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not associated with an organization"
            )
        
        # Parse filters
        filters = {}
        if agent_ids:
            filters['agent_ids'] = [int(id.strip()) for id in agent_ids.split(',')]
        if metric_types:
            filters['metric_types'] = [type.strip() for type in metric_types.split(',')]
        
        export_result = await DashboardService.export_dashboard_report(
            db=db,
            organization_id=current_user.organization_id,
            user_id=current_user.user_id,
            export_type=export_type,
            start_date=start_date,
            end_date=end_date,
            filters=filters
        )
        
        # Prepare response based on export type
        if export_type == "csv":
            return StreamingResponse(
                io.StringIO(export_result["data"]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=dashboard_export_{start_date}_to_{end_date}.csv"
                }
            )
        elif export_type == "pdf":
            return StreamingResponse(
                io.BytesIO(export_result["data"]),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=dashboard_export_{start_date}_to_{end_date}.pdf"
                }
            )
        elif export_type == "json":
            return success_response(
                "Dashboard data exported successfully",
                export_result
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid export type"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting dashboard data: {str(e)}")
        return error_response(
            "Failed to export dashboard data",
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/templates")
async def get_report_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get available report templates"""
    try:
        if not current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not associated with an organization"
            )
        
        templates = await db.execute(
            select(ReportTemplates).where(
                (ReportTemplates.organization_id == current_user.organization_id) |
                (ReportTemplates.is_public == True)
            )
        )
        
        return success_response(
            "Report templates retrieved successfully",
            [template.to_dict() for template in templates.scalars().all()]
        )
        
    except Exception as e:
        logger.error(f"Error fetching report templates: {str(e)}")
        return error_response(
            "Failed to retrieve report templates",
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/templates")
async def create_report_template(
    template_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new report template"""
    try:
        if not current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not associated with an organization"
            )
        
        template = ReportTemplates(
            name=template_data.get("name"),
            description=template_data.get("description"),
            template_type=template_data.get("template_type"),
            metrics_config=template_data.get("metrics_config", {}),
            filters_config=template_data.get("filters_config", {}),
            chart_config=template_data.get("chart_config", {}),
            organization_id=current_user.organization_id,
            created_by=current_user.user_id,
            is_public=template_data.get("is_public", False)
        )
        
        db.add(template)
        await db.commit()
        
        return success_response(
            "Report template created successfully",
            template.to_dict()
        )
        
    except Exception as e:
        logger.error(f"Error creating report template: {str(e)}")
        return error_response(
            "Failed to create report template",
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )