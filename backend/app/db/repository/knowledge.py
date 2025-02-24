from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import insert
from typing import List
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from app.db.models.knowledge import KnowledgeBase
from app.db.models.agent import Agent as AgentDB
from app.db.models.knowledge import agent_knowledge  

#SH:This file will handle the relationship between the Knowledge Base and Agents

async def create_knowledge(db: AsyncSession, agent_id: int, knowledge_ids: List[int]):
    try:
        agent = await db.get(AgentDB, agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found"
            )

        stmt = insert(agent_knowledge).values(
            [{"agent_id": agent_id, "knowledge_id": kid} for kid in knowledge_ids]
        )
        await db.execute(stmt)
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RK01: An error occurred while associating knowledge with agent"
        )
