from fastapi import APIRouter
from app.routes.endpoints.agents import router as agents_router
from app.routes.endpoints.organization import router as organization_router
from app.routes.endpoints.knowledge_base import router as knowledge_router
from app.routes.endpoints.chat import router as chat_router
from app.routes.endpoints.widget import router as widget_router
from app.routes.endpoints.users import router as users_router
from app.routes.endpoints.analytics import router as analytics_router
from app.routes.endpoints.dashboard_analytics import router as dashboard_analytics_router



# MJ: This is our Main Router for all the routes

router = APIRouter()

router.include_router(agents_router, tags=["agents"])
router.include_router(organization_router, tags=["organizations"])
router.include_router(knowledge_router, tags=["knowledge"])
router.include_router(users_router, tags=["users"])
router.include_router(chat_router, tags=["chat"])
router.include_router(widget_router, tags=["widget"])
router.include_router(analytics_router, tags=["analytics"])
router.include_router(dashboard_analytics_router, tags=["dashboard_analytics"])