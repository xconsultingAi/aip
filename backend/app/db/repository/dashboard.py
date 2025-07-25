from sqlalchemy import func, select
from app.db.models.agent import Agent
from app.db.models.chat import Conversation
from app.db.models.knowledge_base import KnowledgeBase
from app.models.user import UserOut
from app.db.repository.chat import get_user_conversation_count
from app.db.repository.agent import get_agent_count
from sqlalchemy.ext.asyncio import AsyncSession

async def get_dashboard_stats(db: AsyncSession, user: UserOut):
    return {
        "agent_count": await get_agent_count(db, user.user_id),
        "conversation_count": await get_user_conversation_count(db, user.user_id),
        "kb_count": await get_org_kb_count(db, user.organization_id),
    }

async def get_org_kb_count(db: AsyncSession, org_id: int) -> int:
    result = await db.execute(
        select(func.count(KnowledgeBase.id))
        .where(KnowledgeBase.organization_id == org_id)
    )
    return result.scalar() or 0