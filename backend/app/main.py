import logging
from fastapi import FastAPI
from dotenv import load_dotenv
from tenacity import RetryError
from app.routes.app_routers import router as app_routers
from app.core.responses import success_response
from datetime import datetime
from app.core.config import settings
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
    retry_error_handler
)
from app.core.dasboard_ws import DashboardWSManager
from app.routes.endpoints.dashboard_ws import router as dashboard_ws_router
from app.core.performance_middleware import PerformanceMiddleware
from app.core.background_task import background_monitor
from app.routes.endpoints.performance import router as performance_router
from app.routes.endpoints.dashboard_analytics import router as dashboard_analytics_router




logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(name)s: %(message)s"
)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# ADD PERFORMANCE MIDDLEWARE
app.add_middleware(PerformanceMiddleware)

# Initialize WebSocket manager
app.state.ws_manager = DashboardWSManager()

# Include all endpoints
app.include_router(app_routers, prefix="/api")
app.include_router(dashboard_ws_router, prefix="/ws")
app.include_router(performance_router, prefix="/api")
app.include_router(dashboard_analytics_router, prefix="/api")


# Register exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)
app.add_exception_handler(RetryError, retry_error_handler)

# Enable CORS (for HTTP requests)
origins = settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS else ["*"]
print("Allowed origins:", origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],   
)
        
# Unsecured route for health check
@app.get("/")
def status():
    return success_response(message="Ready...", data={"timestamp": datetime.now().isoformat()})   