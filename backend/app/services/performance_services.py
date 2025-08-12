from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import func, select, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.performance import SystemMetrics, APIMetrics, AlertRules, SystemAlerts
from app.core.config import settings

class PerformanceService:
    
    @staticmethod
    async def get_system_overview(db: AsyncSession, hours: int = 24) -> Dict:
        """Get system performance overview for the last N hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Check if tables exist first
            tables_exist = await db.execute(text("""
                SELECT 
                    (SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'system_metrics')) as system_exists,
                    (SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'api_metrics')) as api_exists;
            """))
            
            table_status = tables_exist.first()
            
            if not (table_status.system_exists and table_status.api_exists):
                # Return default data if tables don't exist
                return {
                    "time_period_hours": hours,
                    "response_time": {
                        "avg_ms": 0,
                        "max_ms": 0,
                        "min_ms": 0
                    },
                    "error_rate_percent": 0,
                    "total_requests": 0,
                    "error_requests": 0,
                    "system_resources": {
                        "avg_cpu_percent": 0,
                        "avg_memory_percent": 0,
                        "avg_disk_percent": 0
                    },
                    "note": "Performance monitoring tables not yet initialized"
                }
            
            # Response time statistics
            response_time_query = select(
                func.avg(SystemMetrics.response_time_ms).label('avg_response_time'),
                func.max(SystemMetrics.response_time_ms).label('max_response_time'),
                func.min(SystemMetrics.response_time_ms).label('min_response_time')
            ).where(SystemMetrics.timestamp >= cutoff_time)
            
            response_stats = await db.execute(response_time_query)
            response_data = response_stats.first()
            
            # Error rate
            total_requests = await db.execute(
                select(func.count(APIMetrics.id))
                .where(APIMetrics.timestamp >= cutoff_time)
            )
            
            error_requests = await db.execute(
                select(func.count(APIMetrics.id))
                .where(
                    and_(
                        APIMetrics.timestamp >= cutoff_time,
                        APIMetrics.is_error == True
                    )
                )
            )
            
            total_count = total_requests.scalar() or 0
            error_count = error_requests.scalar() or 0
            error_rate = (error_count / total_count * 100) if total_count > 0 else 0
            
            # System resource averages
            resource_query = select(
                func.avg(SystemMetrics.cpu_usage_percent).label('avg_cpu'),
                func.avg(SystemMetrics.memory_usage_percent).label('avg_memory'),
                func.avg(SystemMetrics.disk_usage_percent).label('avg_disk')
            ).where(SystemMetrics.timestamp >= cutoff_time)
            
            resource_stats = await db.execute(resource_query)
            resource_data = resource_stats.first()
            
            return {
                "time_period_hours": hours,
                "response_time": {
                    "avg_ms": round(response_data.avg_response_time or 0, 2),
                    "max_ms": round(response_data.max_response_time or 0, 2),
                    "min_ms": round(response_data.min_response_time or 0, 2)
                },
                "error_rate_percent": round(error_rate, 2),
                "total_requests": total_count,
                "error_requests": error_count,
                "system_resources": {
                    "avg_cpu_percent": round(resource_data.avg_cpu or 0, 2),
                    "avg_memory_percent": round(resource_data.avg_memory or 0, 2),
                    "avg_disk_percent": round(resource_data.avg_disk or 0, 2)
                }
            }
            
        except Exception as e:
            import logging
            logging.error(f"Error in get_system_overview: {str(e)}")
            # Return safe default data
            return {
                "time_period_hours": hours,
                "response_time": {"avg_ms": 0, "max_ms": 0, "min_ms": 0},
                "error_rate_percent": 0,
                "total_requests": 0,
                "error_requests": 0,
                "system_resources": {"avg_cpu_percent": 0, "avg_memory_percent": 0, "avg_disk_percent": 0},
                "error": "Failed to fetch metrics"
            }
    
    @staticmethod
    async def get_endpoint_performance(db: AsyncSession, hours: int = 24) -> List[Dict]:
        """Get performance metrics grouped by endpoint"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Check if tables exist first
            table_check = await db.execute(text())
            
            if not table_check.scalar():
                # Return empty data if table doesn't exist
                return []
            
            query = select(
                APIMetrics.endpoint,
                func.count(APIMetrics.id).label('total_requests'),
                func.avg(APIMetrics.response_time_ms).label('avg_response_time'),
                func.max(APIMetrics.response_time_ms).label('max_response_time'),
                func.sum(func.case((APIMetrics.is_error == True, 1), else_=0)).label('error_count')
            ).where(
                APIMetrics.timestamp >= cutoff_time
            ).group_by(APIMetrics.endpoint).order_by(func.count(APIMetrics.id).desc())
            
            result = await db.execute(query)
            
            endpoints = []
            for row in result.fetchall():
                error_rate = (row.error_count / row.total_requests * 100) if row.total_requests > 0 else 0
                endpoints.append({
                    "endpoint": row.endpoint,
                    "total_requests": row.total_requests,
                    "avg_response_time_ms": round(row.avg_response_time or 0, 2),
                    "max_response_time_ms": round(row.max_response_time or 0, 2),
                    "error_count": row.error_count or 0,
                    "error_rate_percent": round(error_rate, 2)
                })
            
            return endpoints
            
        except Exception as e:
            import logging
            logging.error(f"Error in get_endpoint_performance: {str(e)}")
            # Return empty list on error to prevent 500s
            return []
    
    @staticmethod
    async def get_time_series_data(db: AsyncSession, metric: str, hours: int = 24) -> List[Dict]:
        """Get time series data for a specific metric"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Check if tables exist first
            if metric in ["response_time", "cpu_usage", "memory_usage"]:
                table_check = await db.execute(text())
                
                if not table_check.scalar():
                    return []
            
            elif metric == "error_rate":
                table_check = await db.execute(text())
                
                if not table_check.scalar():
                    return []
            
            # Build the appropriate query based on metric type
            if metric == "response_time":
                query = select(
                    func.date_trunc('hour', SystemMetrics.timestamp).label('hour'),
                    func.avg(SystemMetrics.response_time_ms).label('value')
                ).where(
                    SystemMetrics.timestamp >= cutoff_time
                ).group_by(func.date_trunc('hour', SystemMetrics.timestamp)).order_by('hour')
            
            elif metric == "error_rate":
                # First check if we have any data
                count_check = await db.execute(
                    select(func.count(APIMetrics.id)).where(APIMetrics.timestamp >= cutoff_time)
                )
                
                if count_check.scalar() == 0:
                    return []
                
                query = select(
                    func.date_trunc('hour', APIMetrics.timestamp).label('hour'),
                    (func.sum(func.case((APIMetrics.is_error == True, 1), else_=0)) * 100.0 / func.count(APIMetrics.id)).label('value')
                ).where(
                    APIMetrics.timestamp >= cutoff_time
                ).group_by(func.date_trunc('hour', APIMetrics.timestamp)).order_by('hour')
            
            elif metric == "cpu_usage":
                query = select(
                    func.date_trunc('hour', SystemMetrics.timestamp).label('hour'),
                    func.avg(SystemMetrics.cpu_usage_percent).label('value')
                ).where(
                    SystemMetrics.timestamp >= cutoff_time
                ).group_by(func.date_trunc('hour', SystemMetrics.timestamp)).order_by('hour')
            
            elif metric == "memory_usage":
                query = select(
                    func.date_trunc('hour', SystemMetrics.timestamp).label('hour'),
                    func.avg(SystemMetrics.memory_usage_percent).label('value')
                ).where(
                    SystemMetrics.timestamp >= cutoff_time
                ).group_by(func.date_trunc('hour', SystemMetrics.timestamp)).order_by('hour')
            
            else:
                return []
            
            result = await db.execute(query)
            
            return [
                {
                    "timestamp": row.hour.isoformat() if row.hour else datetime.now().isoformat(),
                    "value": round(row.value or 0, 2)
                }
                for row in result.fetchall()
            ]
            
        except Exception as e:
            import logging
            logging.error(f"Error in get_time_series_data for metric {metric}: {str(e)}")
            # Return empty list instead of raising exception
            return []
    
    @staticmethod
    async def check_alert_conditions(db: AsyncSession):
        """Check all active alert rules and create alerts if conditions are met"""
        try:
            # Check if alert_rules table exists
            table_check = await db.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'alert_rules'
                );
            """))
            
            if not table_check.scalar():
                return
            
            active_rules = await db.execute(
                select(AlertRules).where(AlertRules.is_active == True)
            )
            
            for rule in active_rules.scalars():
                await PerformanceService._check_single_rule(db, rule)
                
        except Exception as e:
            import logging
            logging.error(f"Error in check_alert_conditions: {str(e)}")
    
    @staticmethod
    async def _check_single_rule(db: AsyncSession, rule: AlertRules):
        """Check a single alert rule"""
        try:
            cutoff_time = datetime.now() - timedelta(minutes=rule.time_window_minutes)
            
            if rule.metric_type == "response_time":
                # Check if system_metrics table exists
                table_check = await db.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'system_metrics'
                    );
                """))
                
                if not table_check.scalar():
                    return
                
                query = select(func.avg(SystemMetrics.response_time_ms)).where(
                    SystemMetrics.timestamp >= cutoff_time
                )
                result = await db.execute(query)
                current_value = result.scalar() or 0
            
            elif rule.metric_type == "error_rate":
                # Check if api_metrics table exists
                table_check = await db.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'api_metrics'
                    );
                """))
                
                if not table_check.scalar():
                    return
                
                total_query = select(func.count(APIMetrics.id)).where(APIMetrics.timestamp >= cutoff_time)
                error_query = select(func.count(APIMetrics.id)).where(
                    and_(APIMetrics.timestamp >= cutoff_time, APIMetrics.is_error == True)
                )
                
                total_result = await db.execute(total_query)
                error_result = await db.execute(error_query)
                
                total_count = total_result.scalar() or 0
                error_count = error_result.scalar() or 0
                current_value = (error_count / total_count * 100) if total_count > 0 else 0
            
            elif rule.metric_type == "cpu_usage":
                # Check if system_metrics table exists
                table_check = await db.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'system_metrics'
                    );
                """))
                
                if not table_check.scalar():
                    return
                
                query = select(func.avg(SystemMetrics.cpu_usage_percent)).where(
                    SystemMetrics.timestamp >= cutoff_time
                )
                result = await db.execute(query)
                current_value = result.scalar() or 0
            
            else:
                return
            
            # Check if condition is met
            condition_met = False
            if rule.comparison_operator == ">":
                condition_met = current_value > rule.threshold_value
            elif rule.comparison_operator == "<":
                condition_met = current_value < rule.threshold_value
            elif rule.comparison_operator == ">=":
                condition_met = current_value >= rule.threshold_value
            elif rule.comparison_operator == "<=":
                condition_met = current_value <= rule.threshold_value
            
            if condition_met:
                # Check if system_alerts table exists
                table_check = await db.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'system_alerts'
                    );
                """))
                
                if not table_check.scalar():
                    return
                
                # Check if alert already exists for this rule (avoid spam)
                existing_alert = await db.execute(
                    select(SystemAlerts).where(
                        and_(
                            SystemAlerts.alert_rule_id == rule.id,
                            SystemAlerts.status == 'open',
                            SystemAlerts.created_at >= datetime.now() - timedelta(hours=1)
                        )
                    )
                )
                
                if not existing_alert.scalar():
                    # Create new alert
                    alert = SystemAlerts(
                        alert_rule_id=rule.id,
                        title=f"Alert: {rule.name}",
                        message=f"{rule.metric_type} is {current_value:.2f}, which exceeds threshold of {rule.threshold_value}",
                        severity=rule.severity,
                        trigger_value=current_value,
                        threshold_value=rule.threshold_value
                    )
                    
                    db.add(alert)
                    await db.commit()
                    
        except Exception as e:
            import logging
            logging.error(f"Error in _check_single_rule for rule {rule.id}: {str(e)}")