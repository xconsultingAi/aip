from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.knowledge_base import KnowledgeBase, agent_knowledge 
from app.models.knowledge_base import KnowledgeBaseCreate
from fastapi import HTTPException, status
from sqlalchemy import select
from typing import List, Optional

# SH: This file will contain all the database operations related to the Knowledge base Models

# SH: Create a new knowledge base entry in the database
async def create_knowledge_entry(
    db: AsyncSession, 
    knowledge_data: KnowledgeBaseCreate, 
    file_size: int,
    chunk_count: int,
    knowledge_ids: Optional[List[int]] = None 
):
    # SH: Validate the input data
    if not isinstance(knowledge_data, KnowledgeBaseCreate):
        raise TypeError("knowledge_data must be a KnowledgeBaseCreate instance")

    # SH: If no knowledge_ids are provided, initialize an empty list
    if knowledge_ids is None:
        knowledge_ids = []

    try:
        # SH: Create a new KnowledgeBase ORM object using the provided data
        db_knowledge = KnowledgeBase(
            **knowledge_data.model_dump(),
            file_size=file_size,
            chunk_count=chunk_count
        )
        
        # SH: Add and commit the new knowledge base to the database
        db.add(db_knowledge)
        await db.commit()
        await db.refresh(db_knowledge)  

        # SH: Return a dictionary containing knowledge base details
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
        # SH: Rollback the transaction and raise an HTTP error in case of failure
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

# SH: Get the knowledge base entry linked to a specific agent
async def get_agent_knowledge(db: AsyncSession, agent_id: int):
    
    # SH: Fetch the knowledge base associated with the given agent ID.
    result = await db.execute(
        select(KnowledgeBase)
        .join(agent_knowledge, KnowledgeBase.id == agent_knowledge.c.knowledge_id)
        .where(agent_knowledge.c.agent_id == agent_id)
    )
    knowledge_base = result.scalars().first()
    
    # SH: If no knowledge base is found, raise a 404 error
    if not knowledge_base:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No knowledge base found for this agent"
        )
    return knowledge_base
