from datetime import datetime
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.knowledge_base import KnowledgeBase, TextKnowledge, URLKnowledge, YouTubeKnowledge
from app.models.knowledge_base import KnowledgeBaseCreate
from app.db.models.agent import agent_knowledge
from fastapi import HTTPException, status
from sqlalchemy import select, func
from typing import Any, Dict, List, Optional
from app.core.youtube_processer import YouTubeProcessor
from app.db.models.chat import Conversation

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
        # SH: Create dict from knowledge_data without unpacking it directly
        knowledge_dict = knowledge_data.model_dump()

        # SH: Create a new KnowledgeBase ORM object using the provided data
        db_knowledge = KnowledgeBase(
            file_size=file_size,
            chunk_count=chunk_count,
            **knowledge_dict
        )

        # SH: Add and commit the new knowledge base to the database
        db.add(db_knowledge)
        await db.commit()
        await db.refresh(db_knowledge)

        # SH: Return a dictionary containing knowledge base details
        return {
            "id": db_knowledge.id,
            "name": db_knowledge.name,
            "filename": db_knowledge.filename,
            "content_type": db_knowledge.content_type,
            "format": db_knowledge.format,
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
# SH: Get the knowledge base entry linked to a specific Organization
async def get_organization_knowledge_bases(
    db: AsyncSession, 
    organization_id: int
) -> list[KnowledgeBase]:
    # SH: Retrieve all knowledge bases belonging to a specific organization
    result = await db.execute(
        select(KnowledgeBase)
        .where(KnowledgeBase.organization_id == organization_id)
    )
    return result.scalars().all()

#SH: Get organization knowledge count
async def get_organization_knowledge_count(
    db: AsyncSession, 
    organization_id: int
) -> int:
    # SH: Get count of knowledge bases belonging to a specific organization
    result = await db.execute(
        select(func.count(KnowledgeBase.id))
        .where(KnowledgeBase.organization_id == organization_id)
    )
    return result.scalar_one()

#SH: For Url_knowledge 
async def create_url_knowledge(
    db: AsyncSession,
    name: str,
    url: str,
    organization_id: int,
    file_path: str,
    filename: str,
    content_type: str,  
    file_size: int, 
    chunk_count: int,
    crawl_depth: int = 1,
    include_links: bool = False
) -> URLKnowledge:
    try:
        domain = urlparse(url).netloc.replace('www.', '')
        
        url_knowledge = URLKnowledge(
            name=name,
            filename=filename,
            content_type=content_type,
            format="pdf",
            organization_id=organization_id,
            file_size=file_size,
            chunk_count=chunk_count,
            source_type="url",
            url=url,
            crawl_depth=crawl_depth,
            include_links=include_links,
            last_crawled=datetime.now(),
            file_path=file_path,
            domain_name=domain
        )
        
        db.add(url_knowledge)
        await db.commit()
        await db.refresh(url_knowledge)
        return url_knowledge
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create URL knowledge: {str(e)}"
        )

#SH: Get agent count for knowledge  
async def get_agent_count_for_knowledge(
    db: AsyncSession, 
    kb_id: int, 
    organization_id: int
) -> int:
    # SH: Get count of agents linked to a knowledge base
    kb_exists = await db.execute(
        select(KnowledgeBase)
        .where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.organization_id == organization_id
        )
    )
    #SH: Check if the knowledge base exists
    if not kb_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=404,
            detail="Knowledge base not found in your organization"
        )
    
    #SH: Count linked agents
    agent_count = await db.execute(
        select(func.count(agent_knowledge.c.agent_id))
        .where(agent_knowledge.c.knowledge_id == kb_id)
    )
    return agent_count.scalar_one()        

#SH: Get knowledge format counts
async def get_knowledge_format_counts(
    db: AsyncSession,
    organization_id: int
) -> List[Dict[str, Any]]:
    # SH: Get count of knowledge bases grouped by format for a specific organization
    result = await db.execute(
        select(
            KnowledgeBase.format,
            func.count(KnowledgeBase.id).label("count")
        )
        .where(KnowledgeBase.organization_id == organization_id)
        .group_by(KnowledgeBase.format)
    )
    return [{"format": row.format, "count": row.count} for row in result.all()]

#SH: Create youtube knowledge
async def create_youtube_knowledge(
    db: AsyncSession,
    name: str,
    video_url: str,
    organization_id: int,
    file_path: str,
    transcript: str,
    filename: str,
    format: Optional[str] = None
) -> YouTubeKnowledge:
    try:
        processor = YouTubeProcessor()
        video_id = processor.extract_video_id(video_url)  # Extract video_id here
        
        # Check for existing video first
        existing = await db.execute(
            select(YouTubeKnowledge)
            .where(YouTubeKnowledge.video_id == video_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"YouTube video {video_id} already exists")

        youtube_knowledge = YouTubeKnowledge(
            name=name,
            filename=filename,
            content_type="application/pdf",
            format=format,
            organization_id=organization_id,
            file_size=len(transcript.encode('utf-8')),
            chunk_count=0,
            source_type="youtube",
            video_url=video_url,
            video_id=video_id,  # Use extracted video_id
            transcript_length=len(transcript),
            file_path=file_path
        )
        
        db.add(youtube_knowledge)
        await db.commit()
        await db.refresh(youtube_knowledge)
        return youtube_knowledge
    except ValueError as ve:
        raise ve
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create YouTube knowledge: {str(e)}"
        )

#SH: Create text knowledge
async def create_text_knowledge(
    db: AsyncSession,
    name: str,
    text_content: str,
    organization_id: int,
    file_path: str,
    filename: str,
    content_hash: str,
    format: str
) -> TextKnowledge:
    try:
        text_knowledge = TextKnowledge(
            name=name,
            filename=filename,
            content_type="application/pdf",
            format=format,
            organization_id=organization_id,
            file_size=len(text_content.encode('utf-8')),
            chunk_count=0,  # Will be updated after processing
            source_type="text",
            content_hash=content_hash,
            file_path=file_path
        )
        
        db.add(text_knowledge)
        await db.commit()
        await db.refresh(text_knowledge)
        return text_knowledge
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Text knowledge: {str(e)}"
        )

#SH: Get organization text knowledge count
async def get_organization_text_knowledge_count(
    db: AsyncSession, 
    organization_id: int
) -> int:
    result = await db.execute(
        select(func.count(TextKnowledge.id))
        .where(TextKnowledge.organization_id == organization_id)
    )
    return result.scalar_one()

#SH: Get organization video knowledge count 
async def get_organization_video_knowledge_count(
    db: AsyncSession, 
    organization_id: int
) -> int:
    result = await db.execute(
        select(func.count(YouTubeKnowledge.id))
        .where(YouTubeKnowledge.organization_id == organization_id)
    )
    return result.scalar_one()

#SH: Get agent count for knowledge base
async def get_agent_count_for_knowledge_base(
    db: AsyncSession,
    knowledge_id: int
) -> int:
    result = await db.execute(
        select(func.count(agent_knowledge.c.agent_id))
        .where(agent_knowledge.c.knowledge_id == knowledge_id)
    )
    return result.scalar_one()
