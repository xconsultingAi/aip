from fastapi import APIRouter
from app.routes.endpoints.agents import router as agents_router
from app.routes.endpoints.organization import router as organization_router
from app.routes.endpoints.knowledge_base import router as knowledge_router
from app.routes.endpoints.users import router as users_router

# MJ: This is our Main Router for all the routes

router = APIRouter()

router.include_router(agents_router, tags=["agents"])
router.include_router(organization_router, tags=["organizations"])
router.include_router(knowledge_router, tags=["knowledge"])
router.include_router(users_router, tags=["users"])