from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.knowledge_base import KnowledgeBase, agent_knowledge
from app.models.knowledge_base import KnowledgeBaseCreate
from fastapi import HTTPException, status
from sqlalchemy import select, insert
from typing import List

async def create_knowledge_entry(
    db: AsyncSession, 
    knowledge_data: KnowledgeBaseCreate, 
    file_size: int,
    chunk_count: int,
    agent_id: int,
    knowledge_ids: List[int],
):
    # Check if knowledge_data is a dictionary and convert it
    if isinstance(knowledge_data, dict):
        knowledge_data = KnowledgeBaseCreate(**knowledge_data)
    
    # Ensure knowledge_data is an instance of KnowledgeBaseCreate
    if not isinstance(knowledge_data, KnowledgeBaseCreate):
        raise TypeError("knowledge_data must be a KnowledgeBaseCreate instance")
    
    # Rest of your code...
    try:
        # Step 1: Insert into `KnowledgeBase`
        db_knowledge = KnowledgeBase(
            **knowledge_data.model_dump(),
            file_size=file_size,
            chunk_count=chunk_count
        )
        db.add(db_knowledge)
        await db.commit()
        await db.refresh(db_knowledge)

        # Step 2: Link each knowledge base to the agent in `agent_knowledge` table
        for knowledge_id in knowledge_ids:
            stmt = insert(agent_knowledge).values(agent_id=agent_id, knowledge_id=db_knowledge.id)
            await db.execute(stmt)

        await db.commit()

        # Return all required fields for KnowledgeBaseOut
        return {
            "id": db_knowledge.id,
            "filename": db_knowledge.filename,
            "content_type": db_knowledge.content_type,
            "organization_id": db_knowledge.organization_id,
            "uploaded_at": db_knowledge.uploaded_at,
            "file_size": db_knowledge.file_size,
            "chunk_count": db_knowledge.chunk_count
        }
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
        
print(f"Type of KnowledgeBaseCreate: {type(KnowledgeBaseCreate)}")