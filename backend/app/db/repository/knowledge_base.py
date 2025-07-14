from datetime import datetime
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.knowledge_base import KnowledgeBase, TextKnowledge, URLKnowledge, YouTubeKnowledge, Category, Tag, knowledge_tag
from app.models.knowledge_base import KnowledgeBaseCreate, KnowledgeUpdate
from app.db.models.agent import agent_knowledge
from fastapi import HTTPException, logger, status
from sqlalchemy import or_, select, func
from typing import Any, Dict, List, Optional
from app.core.youtube_processer import YouTubeProcessor
from sqlalchemy.orm import aliased
from sqlalchemy.orm import selectinload

# SH: This file will contain all the database operations related to the Knowledge base Models

# SH: Create a new knowledge base entry in the database
async def create_knowledge_entry(
    db: AsyncSession,
    knowledge_data: KnowledgeBaseCreate,
    file_size: int,
    chunk_count: int,
    knowledge_ids: Optional[List[int]] = None
) -> KnowledgeBase:  # Change return type to KnowledgeBase
    if not isinstance(knowledge_data, KnowledgeBaseCreate):
        raise TypeError("knowledge_data must be a KnowledgeBaseCreate instance")

    try:
        # Create the knowledge base record
        db_knowledge = KnowledgeBase(
            name=knowledge_data.name,
            filename=knowledge_data.filename,
            content_type=knowledge_data.content_type,
            format=knowledge_data.format,
            organization_id=knowledge_data.organization_id,
            file_size=file_size,
            chunk_count=chunk_count,
            source_type="file"  # Make sure this matches your model
        )

        db.add(db_knowledge)
        await db.commit()
        await db.refresh(db_knowledge)
        
        # Return the SQLAlchemy model object
        return db_knowledge

    except Exception as e:
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
    format: str,
    crawl_depth: int = 1,
    include_links: bool = False
) -> URLKnowledge:
    try:
        domain = urlparse(url).netloc.replace('www.', '')
        #SH: Create a new URLKnowledge object
        url_knowledge = URLKnowledge(
            name=name,
            filename=filename,
            content_type=content_type,
            format=format,
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
        #SH: Add the URLKnowledge object to the database
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
        #SH: Process the youtube video and get the transcript
        processor = YouTubeProcessor()
        video_id = processor.extract_video_id(video_url)
        #SH: Check for existing video
        existing = await db.execute(
            select(YouTubeKnowledge)
            .where(YouTubeKnowledge.video_id == video_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"YouTube video {video_id} already exists")

        #SH: Explicitly define fields to avoid passing unexpected ones
        youtube_knowledge_data = {
            "name": name,
            "filename": filename,
            "content_type": "application/pdf",
            "format": format,
            "organization_id": organization_id,
            "file_size": len(transcript.encode('utf-8')),
            "chunk_count": 0,
            "source_type": "youtube",
            "video_url": video_url,
            "video_id": video_id,
            "transcript_length": len(transcript),
            "file_path": file_path
        }
        #SH: Create a new YouTubeKnowledge object
        youtube_knowledge = YouTubeKnowledge(**youtube_knowledge_data)
        #SH: Add the YouTubeKnowledge object to the database
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
        #SH: Create a new TextKnowledge object
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
        #SH: Add the TextKnowledge object to the database
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

# SH: Category CRUD operations

async def create_category(db: AsyncSession, category_data: dict):
    try:
        category = Category(**category_data)
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

async def get_category(db: AsyncSession, category_id: int, organization_id: int):
    result = await db.execute(
        select(Category)
        .where(
            Category.id == category_id,
            Category.organization_id == organization_id
        )
    )
    return result.scalar_one_or_none()

async def get_categories(db: AsyncSession, organization_id: int):
    result = await db.execute(
        select(Category)
        .where(Category.organization_id == organization_id)
        .order_by(Category.name)
    )
    return result.scalars().all()

async def get_category_tree(db: AsyncSession, organization_id: int) -> List[dict]:
    # SH: Get all categories with their children loaded
    result = await db.execute(
        select(Category)
        .where(Category.organization_id == organization_id)
        .options(
            selectinload(Category.children)
        )
        .order_by(Category.name)
    )
    categories = result.scalars().all()

    # SH: Build tree structure with all required fields
    def build_tree(category: Category) -> dict:
        return {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "parent_id": category.parent_id,
            "organization_id": category.organization_id,
            "created_at": category.created_at,
            "updated_at": category.updated_at,
            "children": [build_tree(child) for child in category.children]
        }

    # SH: Only return root categories (where parent_id is None)
    tree = [build_tree(c) for c in categories if c.parent_id is None]
    return tree

async def update_category(db: AsyncSession, category_id: int, organization_id: int, update_data: dict):
    category = await get_category(db, category_id, organization_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    for field, value in update_data.items():
        setattr(category, field, value)
    
    await db.commit()
    await db.refresh(category)
    return category

async def delete_category(db: AsyncSession, category_id: int, organization_id: int):
    category = await get_category(db, category_id, organization_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # SH: Check if category has children
    result = await db.execute(
        select(func.count(Category.id))
        .where(Category.parent_id == category_id)
    )
    child_count = result.scalar_one()
    
    if child_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete category with subcategories. Move or delete subcategories first."
        )
    
    # SH: Check if category has knowledge bases
    result = await db.execute(
        select(func.count(KnowledgeBase.id))
        .where(KnowledgeBase.category_id == category_id)
    )
    kb_count = result.scalar_one()
    
    if kb_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete category with knowledge bases. Reassign knowledge bases first."
        )
    
    await db.delete(category)
    await db.commit()
    return True

# SH: Tag CRUD operations
async def create_tag(db: AsyncSession, tag_data: dict):
    try:
        # Check if tag with same name already exists for organization
        existing = await db.execute(
            select(Tag)
            .where(
                Tag.name == tag_data['name'],
                Tag.organization_id == tag_data['organization_id']
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Tag with this name already exists"
            )
            
        tag = Tag(**tag_data)
        db.add(tag)
        await db.commit()
        await db.refresh(tag)
        return tag
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

async def get_tag(db: AsyncSession, tag_id: int, organization_id: int):
    result = await db.execute(
        select(Tag)
        .where(
            Tag.id == tag_id,
            Tag.organization_id == organization_id
        )
    )
    return result.scalar_one_or_none()

async def get_tags(db: AsyncSession, organization_id: int, search: str = None):
    query = select(Tag).where(Tag.organization_id == organization_id)
    
    if search:
        query = query.where(Tag.name.ilike(f"%{search}%"))
    
    query = query.order_by(Tag.name)
    
    result = await db.execute(query)
    return result.scalars().all()

async def update_tag(db: AsyncSession, tag_id: int, organization_id: int, name: str):
    tag = await get_tag(db, tag_id, organization_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    # SH: Check if new name already exists
    existing = await db.execute(
        select(Tag)
        .where(
            Tag.name == name,
            Tag.organization_id == organization_id,
            Tag.id != tag_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Tag with this name already exists"
        )
    
    tag.name = name
    await db.commit()
    await db.refresh(tag)
    return tag

async def delete_tag(db: AsyncSession, tag_id: int, organization_id: int):
    tag = await get_tag(db, tag_id, organization_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    # SH: Check if tag is used by any knowledge base
    result = await db.execute(
        select(func.count(knowledge_tag.c.knowledge_id))
        .where(knowledge_tag.c.tag_id == tag_id)
    )
    kb_count = result.scalar_one()
    
    if kb_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete tag that is assigned to knowledge bases. Remove tag assignments first."
        )
    
    await db.delete(tag)
    await db.commit()
    return True

async def update_knowledge_categories_tags(
    db: AsyncSession,
    knowledge_id: int,
    organization_id: int,
    update_data: KnowledgeUpdate
):
    # SH: Fetch knowledge base
    result = await db.execute(
        select(KnowledgeBase)
        .options(
            selectinload(KnowledgeBase.category),
            selectinload(KnowledgeBase.tags)
        )
        .where(
            KnowledgeBase.id == knowledge_id,
            KnowledgeBase.organization_id == organization_id
        )
    )
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # SH: Update category if provided
    if update_data.category_id is not None:
        if update_data.category_id == 0:  # Remove category
            kb.category = None
        else:
            result = await db.execute(
                select(Category).where(
                    Category.id == update_data.category_id,
                    Category.organization_id == organization_id
                )
            )
            category = result.scalar_one_or_none()
            if not category:
                raise HTTPException(status_code=404, detail="Category not found")
            kb.category = category

    # SH: Update tags if provided
    if update_data.tag_ids is not None:
        result = await db.execute(
            select(Tag).where(
                Tag.id.in_(update_data.tag_ids),
                Tag.organization_id == organization_id
            )
        )
        kb.tags = result.scalars().all()

    try:
        await db.commit()
        await db.refresh(kb)
        return kb
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error during update: {str(e)}"
        )
        
async def get_knowledge_by_category(
    db: AsyncSession,
    organization_id: int,
    category_id: Optional[int] = None,
    include_subcategories: bool = False
) -> List[KnowledgeBase]:
    query = select(KnowledgeBase).where(
        KnowledgeBase.organization_id == organization_id
    ).options(
        selectinload(KnowledgeBase.category),
        selectinload(KnowledgeBase.tags)
    )
    
    if category_id is not None:
        if include_subcategories:
            # SH: Get all subcategory IDs
            CategoryAlias = aliased(Category)
            subq = (
                select(CategoryAlias.id)
                .where(CategoryAlias.parent_id == category_id)
                .cte(recursive=True)
            )
            subq = subq.union_all(
                select(CategoryAlias.id)
                .join(subq, CategoryAlias.parent_id == subq.c.id)
            )
            query = query.where(
                or_(
                    KnowledgeBase.category_id == category_id,
                    KnowledgeBase.category_id.in_(select(subq.c.id))
                )
            )
        else:
            query = query.where(KnowledgeBase.category_id == category_id)
    else:
        query = query.where(KnowledgeBase.category_id.is_(None))
    
    result = await db.execute(query.order_by(KnowledgeBase.name))
    return result.scalars().all()

async def get_knowledge_by_tag(
    db: AsyncSession,
    organization_id: int,
    tag_id: int
) -> List[KnowledgeBase]:
    result = await db.execute(
        select(KnowledgeBase)
        .options(
            selectinload(KnowledgeBase.category),
            selectinload(KnowledgeBase.tags)
        )
        .join(KnowledgeBase.tags)
        .where(
            KnowledgeBase.organization_id == organization_id,
            Tag.id == tag_id
        )
        .order_by(KnowledgeBase.name)
    )
    return result.scalars().all()

# SH: search function
async def search_knowledge(
    db: AsyncSession,
    query: str,
    organization_id: int,
    file_types: Optional[List[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    category_id: Optional[int] = None,
    tag_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 10
) -> tuple[list, int]:
    try:
        # SH: Base query
        stmt = select(KnowledgeBase).options(
            selectinload(KnowledgeBase.category),
            selectinload(KnowledgeBase.tags)
        ).where(KnowledgeBase.organization_id == organization_id)
        
        # SH: Keyword search across name, category, and tags
        if query:
            stmt = stmt.join(KnowledgeBase.category, isouter=True)
            stmt = stmt.join(KnowledgeBase.tags, isouter=True)
            stmt = stmt.where(or_(
                KnowledgeBase.name.ilike(f"%{query}%"),
                Category.name.ilike(f"%{query}%"),
                Tag.name.ilike(f"%{query}%")
            ))
        
        # SH: Apply filters
        if file_types:
            stmt = stmt.where(KnowledgeBase.format.in_(file_types))
        if start_date:
            stmt = stmt.where(KnowledgeBase.uploaded_at >= start_date)
        if end_date:
            stmt = stmt.where(KnowledgeBase.uploaded_at <= end_date)
        if category_id:
            stmt = stmt.where(KnowledgeBase.category_id == category_id)
        if tag_id:
            stmt = stmt.join(knowledge_tag).where(knowledge_tag.c.tag_id == tag_id)
        
        # SH: Get total count
        count_query = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()
        
        # SH: Apply pagination
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        # SH: Execute query
        result = await db.execute(stmt)
        knowledge_bases = result.scalars().unique().all()
        
        return knowledge_bases, total
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search error: {str(e)}"
        )
