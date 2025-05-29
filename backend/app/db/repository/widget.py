from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models.widget import WidgetSession
from fastapi import HTTPException

#SH: Create widget session
async def create_widget_session(
    db: AsyncSession, 
    visitor_id: str, 
    agent_id: int
) -> WidgetSession:
    session = WidgetSession(visitor_id=visitor_id, agent_id=agent_id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

#SH: Update widget session
async def update_widget_session(
    db: AsyncSession,
    visitor_id: str,
    **kwargs
) -> WidgetSession:
    result = await db.execute(
        select(WidgetSession).where(WidgetSession.visitor_id == visitor_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    for key, value in kwargs.items():
        setattr(session, key, value)
    
    await db.commit()
    await db.refresh(session)
    return session