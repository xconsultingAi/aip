import time
import logging
import psutil # type: ignore
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import SessionLocal
from app.db.models.performance import SystemMetrics, APIMetrics

logger = logging.getLogger(__name__)

class PerformanceMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/docs", "/redoc", "/openapi.json", "/favicon.ico"]
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Skip monitoring for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        response = None
        error_message = None
        status_code = 500
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            error_message = str(e)
            logger.error(f"Request failed: {error_message}")
            # Create a basic error response
            response = Response(content="Internal Server Error", status_code=500)
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=None)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        # Store metrics asynchronously
        await self._store_metrics(
            request, response_time, status_code, error_message,
            cpu_percent, memory_percent, disk_percent
        )
        
        # Add performance headers
        if response:
            response.headers["X-Response-Time"] = f"{response_time:.2f}ms"
            response.headers["X-Process-Time"] = f"{time.time() - start_time:.4f}s"
        
        return response
    
    async def _store_metrics(self, request: Request, response_time: float, 
                           status_code: int, error_message: str,
                           cpu_percent: float, memory_percent: float, disk_percent: float):
        try:
            async with SessionLocal() as db:
                now = datetime.now()
                
                # System metrics
                system_metric = SystemMetrics(
                    response_time_ms=response_time,
                    cpu_usage_percent=cpu_percent,
                    memory_usage_percent=memory_percent,
                    disk_usage_percent=disk_percent,
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=status_code,
                    error_message=error_message,
                    date_bucket=now.strftime("%Y-%m-%d"),
                    hour_bucket=now.hour
                )
                
                # API metrics
                user_id = getattr(request.state, 'user_id', None)
                org_id = getattr(request.state, 'organization_id', None)
                
                api_metric = APIMetrics(
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=status_code,
                    response_time_ms=response_time,
                    user_id=user_id,
                    organization_id=org_id,
                    is_error=status_code >= 400,
                    error_type=type(Exception).__name__ if error_message else None,
                    error_message=error_message,
                    date_bucket=now.strftime("%Y-%m-%d"),
                    hour_bucket=now.hour
                )
                
                db.add(system_metric)
                db.add(api_metric)
                await db.commit()
                
        except Exception as e:
            logger.error(f"Failed to store metrics: {e}")