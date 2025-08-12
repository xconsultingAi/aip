import asyncio
import logging
from datetime import datetime, timedelta
from app.db.database import SessionLocal
from app.services.performance_services import PerformanceService

logger = logging.getLogger(__name__)

class BackgroundMonitor:
    def __init__(self):
        self.is_running = False
        self.alert_check_interval = 300  # 5 minutes
        self.cleanup_interval = 86400    # 24 hours
    
    async def start(self):
        # Start background monitoring tasks
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("Starting background monitoring tasks")
        
        # Start alert checking task
        asyncio.create_task(self._alert_check_loop())
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_loop())
    
    async def stop(self):
        """Stop background monitoring"""
        self.is_running = False
        logger.info("Stopping background monitoring tasks")
    
    async def _alert_check_loop(self):
        """Continuously check alert conditions"""
        while self.is_running:
            try:
                async with SessionLocal() as db:
                    await PerformanceService.check_alert_conditions(db)
                logger.debug("Alert conditions checked")
            except Exception as e:
                logger.error(f"Error in alert check loop: {e}")
            
            await asyncio.sleep(self.alert_check_interval)
    
    async def _cleanup_loop(self):
        """Clean up old metrics data"""
        while self.is_running:
            try:
                await self._cleanup_old_metrics()
                logger.info("Metrics cleanup completed")
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
            
            await asyncio.sleep(self.cleanup_interval)
    
    async def _cleanup_old_metrics(self):
        """Remove metrics older than 30 days"""
        cutoff_date = datetime.now() - timedelta(days=30)
        
        async with SessionLocal() as db:
            from app.db.models.performance import SystemMetrics, APIMetrics
            from sqlalchemy import delete
            
            # Delete old system metrics
            await db.execute(
                delete(SystemMetrics).where(SystemMetrics.timestamp < cutoff_date)
            )
            
            # Delete old API metrics
            await db.execute(
                delete(APIMetrics).where(APIMetrics.timestamp < cutoff_date)
            )
            
            await db.commit()

# Global instance
background_monitor = BackgroundMonitor()