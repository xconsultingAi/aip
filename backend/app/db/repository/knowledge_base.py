from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.knowledge_base import KnowledgeBase, agent_knowledge 
from app.models.knowledge_base import KnowledgeBaseCreate
from fastapi import HTTPException, status
from sqlalchemy import select, insert
from typing import List, Optional

async def create_knowledge_entry(
    db: AsyncSession, 
    knowledge_data: KnowledgeBaseCreate, 
    file_size: int,
    chunk_count: int,
    agent_id: Optional[int] = None, 
    knowledge_ids: Optional[List[int]] = None 
):
    # knowledge_data is an instance of KnowledgeBaseCreate
    if not isinstance(knowledge_data, KnowledgeBaseCreate):
        raise TypeError("knowledge_data must be a KnowledgeBaseCreate instance")
    
    # knowledge_ids is a list
    if knowledge_ids is None:
        knowledge_ids = []

    try:
        # Insert into KnowledgeBase
        db_knowledge = KnowledgeBase(
            **knowledge_data.model_dump(),
            file_size=file_size,
            chunk_count=chunk_count,
            agent_id=agent_id 
        )
        db.add(db_knowledge)
        await db.commit()
        await db.refresh(db_knowledge)  

        # Link the new knowledge base to the agent
        if agent_id:
            # Link the newly created knowledge base to the agent
            stmt = insert(agent_knowledge).values(
                agent_id=agent_id,
                knowledge_id=db_knowledge.id
            )
            await db.execute(stmt)
            await db.commit()

        # Return the knowledge base entry as a dictionary
        return {
            "id": db_knowledge.id,
            "filename": db_knowledge.filename,
            "content_type": db_knowledge.content_type,
            "organization_id": db_knowledge.organization_id,
            "uploaded_at": db_knowledge.uploaded_at.isoformat() if db_knowledge.uploaded_at else None,
            "file_size": db_knowledge.file_size,
            "chunk_count": db_knowledge.chunk_count
        }
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

async def get_agent_knowledge(db: AsyncSession, agent_id: int):
    """
    Fetch the knowledge base linked to the agent.
    """
    result = await db.execute(
        select(KnowledgeBase)
        .join(agent_knowledge, KnowledgeBase.id == agent_knowledge.c.knowledge_id)
        .where(agent_knowledge.c.agent_id == agent_id)
    )
    knowledge_base = result.scalars().first()
    
    if not knowledge_base:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No knowledge base found for this agent"
        )
    
    return knowledge_base