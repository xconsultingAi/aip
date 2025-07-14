import logging
from fastapi import APIRouter, Body, Form, HTTPException, UploadFile, File, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.db.database import get_db
from app.db.models.user import User
from app.db.models.knowledge_base import KnowledgeBase
from app.services.knowledge_services import (create_category_service, 
create_tag_service, delete_category_service, delete_tag_service, get_categories_service,
get_category_service, get_category_tree_service, get_knowledge_by_category_service,
get_knowledge_by_tag_service, get_tag_service, get_tags_service,
process_file, process_text, process_url, process_youtube, search_knowledge_service, update_category_service,
update_tag_service)
from app.db.repository.knowledge_base import create_knowledge_entry, get_agent_count_for_knowledge_base, update_knowledge_categories_tags
from app.dependencies.auth import get_current_user
from app.models.knowledge_base import (
    KnowledgeBaseOut, KnowledgeBaseCreate, KnowledgeFormatCount, 
    KnowledgeBaseAgentCount, KnowledgeSearchRequest, KnowledgeSearchResponse, KnowledgeURL, OrganizationKnowledgeCount, 
    TextKnowledgeRequest, YouTubeKnowledgeRequest,
    CategoryCreate, CategoryOut, CategoryTree, TagCreate, TagOut, KnowledgeUpdate
)

from app.core.responses import success_response, error_response
import os
import uuid
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import selectinload


#SH: This is our Main Router for all the routes related to Knowledge base
router = APIRouter(tags=["knowledge"])
logger = logging.getLogger(__name__)

#SH: Upload knowledge base  
@router.post("/upload_knowledge_base", response_model=KnowledgeBaseOut)
async def upload_knowledge(
    file: UploadFile = File(..., description="Select only PDF, DOCX, HTML, CSV, XLS or XLSX", media_type=settings.ALLOWED_CONTENT_TYPES),
    name: str = Form(..., description="Knowledge base display name"), 
    kb_format: str = Form(..., description="File format (pdf, docx, txt, html, csv, xls, xlsx)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    #SH: Ensure user belongs to an organization
    if not current_user.organization_id:
        return error_response("User must belong to an organization to upload KB", 400)
    
    #SH: Validate file type
    if file.content_type not in settings.ALLOWED_CONTENT_TYPES:
        return error_response(
            f"Unsupported file type. Allowed formats: {', '.join(settings.ALLOWED_CONTENT_TYPES)}",
            400
        )

    #SH: Validate file extension matches selected format
    file_extension = Path(file.filename).suffix.lstrip('.').lower()
    if file_extension != kb_format.lower():
        return error_response(
            f"Selected format '{kb_format}' does not match uploaded file extension '.{file_extension}'",
            400
        )

    try:
        #SH: Read file content and reset cursor
        content = await file.read()
        file.file.seek(0)
        file_size = len(content)

        if file_size > settings.MAX_FILE_SIZE:
            return error_response("File size exceeds limit", 400)

        #SH: Generate unique filename
        ext = Path(file.filename).suffix
        unique_id = uuid.uuid4().hex[:8]
        unique_filename = f"{unique_id}{ext}"
        file_path = os.path.join(settings.KNOWLEDGE_DIR, unique_filename)

        #SH: Save file
        os.makedirs(settings.KNOWLEDGE_DIR, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(content)

        #SH: Create database entry first with chunk_count=0
        knowledge_data = KnowledgeBaseCreate(
            name=name,
            filename=unique_filename,
            content_type=file.content_type,
            format=kb_format.lower(),
            organization_id=current_user.organization_id
        )

        db_entry = await create_knowledge_entry(
            db=db,
            knowledge_data=knowledge_data,
            file_size=file_size,
            chunk_count=0  # Temporary value, will be updated
        )

        #SH: Process file with the knowledge_base_id
        chunk_count = process_file(file_path, file.content_type, current_user.organization_id, db_entry.id)

        #SH: Update the chunk count in the database
        db_entry.chunk_count = chunk_count
        await db.commit()

        #SH: Load relationships (e.g. tags)
        result = await db.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.id == db_entry.id)
            .options(selectinload(KnowledgeBase.tags))
        )
        db_entry_with_relations = result.scalar_one()

        return success_response(
            "File uploaded and processed",
            KnowledgeBaseOut.model_validate(db_entry_with_relations)
        )

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        #SH: Cleanup file if it exists
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return error_response(str(e), 500)
    
#SH: Get organization knowledge bases
@router.get("/org_knowledge_base", response_model=list[KnowledgeBaseOut])
async def get_organization_knowledge_bases(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # SH: Ensure user belongs to an organization
    if not current_user.organization_id:
        return error_response("User must belong to an organization to access knowledge bases", 400)
    
    # SH: Fetch knowledge bases for the user's organization
    result = await db.execute(
        select(KnowledgeBase)
        .where(KnowledgeBase.organization_id == current_user.organization_id)
    )
    knowledge_bases = result.scalars().all()
    
    return success_response(
        "Organization knowledge bases retrieved",
        [KnowledgeBaseOut.model_validate(kb.__dict__) for kb in knowledge_bases]
    )

#SH: Get organization knowledge count
@router.get("/org_knowledge_count", response_model=OrganizationKnowledgeCount)
async def get_organization_knowledge_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    #SH: Get count of knowledge bases for the current user's organization
    #SH: Ensure user belongs to an organization
    if not current_user.organization_id:
        return error_response("User must belong to an organization", 400)
    
    try:
        #SH: Import the repository function explicitly to avoid naming conflicts
        from app.db.repository.knowledge_base import get_organization_knowledge_count as repo_count
        count = await repo_count(db, current_user.organization_id)
        
        return {
            "organization_id": current_user.organization_id,
            "total_knowledge_bases": count
        }
    except Exception as e:
        logger.error(f"Error getting knowledge base count: {str(e)}")
        return error_response("Could not retrieve knowledge base count", 500)

#SH: Route for Url Scraping
@router.post("/add_url")
async def add_knowledge_from_url(
    url_data: KnowledgeURL = Body(..., description="URL and scraping options"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
): 
    if not current_user.organization_id:
        raise HTTPException(400, "User organization not set")

    # Additional format validation (though Pydantic already handles this)
    if url_data.format.lower() not in [fmt.lower() for fmt in settings.ALLOWED_URL_FORMATS]:
        raise HTTPException(
            400,
            detail=f"Invalid format. Allowed formats: {', '.join(settings.ALLOWED_URL_FORMATS)}"
        )

    try:
        logger.info(f"Calling process_url with url_data={url_data}, organization_id={current_user.organization_id}, db={db}")
        result = await process_url(url_data, current_user.organization_id, db)
        return success_response(
            message="URL content added to knowledge base",
            data=result
        )
    except ValueError as e:
        logger.error(f"ValueError in add_knowledge_from_url: {str(e)}")
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        logger.exception("URL processing failed")
        raise HTTPException(500, "Internal processing error")


#SH: Route for Count of agents against the Knowledge_base
@router.get("/format_count", response_model=list[KnowledgeFormatCount])
async def get_knowledge_format_counts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    #SH: Get count of knowledge bases grouped by file format for the organization
    if not current_user.organization_id:
        return error_response("User must belong to an organization", 400)
    
    try:
        from app.db.repository.knowledge_base import get_knowledge_format_counts
        counts = await get_knowledge_format_counts(db, current_user.organization_id)
        return success_response(
            "Format counts retrieved successfully",
            counts
        )
    except Exception as e:
        logger.error(f"Error getting format counts: {str(e)}")
        return error_response("Could not retrieve format counts", 500)
    
#SH: Route for Youtube
@router.post("/add_youtube")
async def add_youtube_video(
    youtube_data: YouTubeKnowledgeRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.organization_id:
        return error_response("Organization membership required", 403)
    
    # Additional format validation
    if youtube_data.format.lower() not in ["video", "audio"]:
        raise HTTPException(
            400,
            detail="Invalid format. Allowed formats: video, audio"
        )

    try:
        result = await process_youtube(youtube_data, current_user.organization_id, db)
        return success_response(
            result.get("message", "YouTube video processed successfully"),
            {k: v for k, v in result.items() if k != "message"}
        )
    except HTTPException as e:
        return error_response(e.detail, e.status_code)
    except Exception as e:
        logger.error(f"Endpoint error: {str(e)}")
        return error_response("Internal server error", 500)

#SH: Route for Text
@router.post("/add_text")
async def add_knowledge_from_text(
    text_data: TextKnowledgeRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):      
    #SH: Ensure user belongs to an organization
    if not current_user.organization_id:
        raise HTTPException(400, "User organization not set")
    
    #SH: Validate format
    if text_data.format.lower() not in ["text", "article"]:
        raise HTTPException(400, detail="Invalid format. Allowed formats: text, article")

    try:
        result = await process_text(text_data, current_user.organization_id, db)
        return success_response("Text content added to knowledge base", result)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception:
        raise HTTPException(500, "Internal processing error")

#SH: Get agent count for knowledge base
@router.get("/agent_count", response_model=KnowledgeBaseAgentCount)
async def get_agent_count(
        knowledge_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
        if not current_user.organization_id:
            return error_response("User must belong to an organization", 400)
        
        try:
            count = await get_agent_count_for_knowledge_base(db, knowledge_id)
            return success_response(
                "Agent count retrieved",
                KnowledgeBaseAgentCount(
                    knowledge_id=knowledge_id,
                    agent_count=count
                )
            )
        except Exception as e:
            logger.error(f"Error getting agent count: {str(e)}")
            return error_response("Could not retrieve agent count", 500)
# SH: Category Routes

# SH: Create a new category for the user's organization
@router.post("/categories", response_model=CategoryOut)
async def create_category(
    category_data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # SH: Ensure the user is part of an organization
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")
    
    # SH: Assign organization ID to the new category
    category_data.organization_id = current_user.organization_id
    return await create_category_service(db, category_data)

# SH: Get hierarchical tree of all categories in the user's organization
@router.get("/categories/tree", response_model=List[CategoryTree])
async def get_category_tree(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # SH: Ensure the user is part of an organization
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")
    
    return await get_category_tree_service(db, current_user.organization_id)

# SH: Get flat list of categories for the user's organization
@router.get("/categories", response_model=List[CategoryOut])
async def get_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # SH: Ensure the user is part of an organization
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")
    
    return await get_categories_service(db, current_user.organization_id)

# SH: Get a specific category by its ID
@router.get("/categories/{category_id}", response_model=CategoryOut)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # SH: Ensure the user is part of an organization
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")
    
    return await get_category_service(db, category_id, current_user.organization_id)

# SH: Update an existing category
@router.put("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    update_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # SH: Ensure the user is part of an organization
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")
    
    return await update_category_service(
        db, category_id, current_user.organization_id, update_data
    )

# SH: Delete a category by ID
@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # SH: Ensure the user is part of an organization
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")
    
    success = await delete_category_service(
        db, category_id, current_user.organization_id
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete category")
    return {"message": "Category deleted successfully"}

# SH: Tag Routes

# SH: Create a new tag for the user's organization
@router.post("/tags", response_model=TagOut)
async def create_tag(
    tag_data: TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # SH: Ensure the user is part of an organization
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")
    
    tag_data.organization_id = current_user.organization_id
    return await create_tag_service(db, tag_data)

# SH: Get a tag by ID
@router.get("/tags/{tag_id}", response_model=TagOut)
async def get_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # SH: Ensure the user is part of an organization
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")
    
    return await get_tag_service(db, tag_id, current_user.organization_id)

# SH: Get a list of tags, optionally filtered by search
@router.get("/tags", response_model=List[TagOut])
async def get_tags(
    search: Optional[str] = Query(None, min_length=1, max_length=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # SH: Ensure the user is part of an organization
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")
    
    return await get_tags_service(db, current_user.organization_id, search)

# SH: Update a tag's name
@router.put("/tags/{tag_id}", response_model=TagOut)
async def update_tag(
    tag_id: int,
    name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # SH: Ensure the user is part of an organization
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")
    
    return await update_tag_service(
        db, tag_id, current_user.organization_id, name
    )

# SH: Delete a tag by ID
@router.delete("/tags/{tag_id}")
async def delete_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # SH: Ensure the user is part of an organization
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")
    
    success = await delete_tag_service(
        db, tag_id, current_user.organization_id
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete tag")
    return {"message": "Tag deleted successfully"}

# SH: Knowledge Base Categorization Routes

# SH: Assign categories and tags to a knowledge base item
@router.put("/knowledge/{knowledge_id}/categorize")
async def update_knowledge_categories(
    knowledge_id: int,
    update_data: KnowledgeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # SH: Ensure the user is part of an organization
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")
    
    try:
        # SH: Perform update using service
        updated_kb = await update_knowledge_categories_tags(
            db=db,
            knowledge_id=knowledge_id,
            organization_id=current_user.organization_id,
            update_data=update_data
        )
        return KnowledgeBaseOut.model_validate(updated_kb)
    except HTTPException:
        raise
    except Exception as e:
        # SH: Handle unexpected errors
        logger.error(f"Failed to update knowledge base: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update knowledge base: {str(e)}"
        )

# SH: Retrieve knowledge base items by category (with optional subcategories)
@router.get("/knowledge/by-category")
async def get_knowledge_by_category(
    category_id: Optional[int] = Query(None),
    include_subcategories: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # SH: Ensure the user is part of an organization
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")
    
    return await get_knowledge_by_category_service(
        db=db,
        organization_id=current_user.organization_id,
        category_id=category_id,
        include_subcategories=include_subcategories
    )

# SH: Retrieve knowledge base items by tag
@router.get("/knowledge/by-tag/{tag_id}")
async def get_knowledge_by_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # SH: Ensure the user is part of an organization
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization")
    
    return await get_knowledge_by_tag_service(
        db=db,
        organization_id=current_user.organization_id,
        tag_id=tag_id
    )

# SH: Search endpoint for knowledge base
@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge_base(
    search_request: KnowledgeSearchRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # SH: Ensure the user is part of an organization
    if not current_user.organization_id:
        return error_response("User must belong to an organization to search KB", 400)
    
    try:
        # SH: Perform search using service
        search_result = await search_knowledge_service(
            db=db,
            search_request=search_request,
            organization_id=current_user.organization_id
        )
        return success_response("Search completed", search_result)
    except HTTPException as e:
        return error_response(e.detail, e.status_code)
    except Exception as e:
        # SH: Handle unexpected errors
        logger.error(f"Search endpoint error: {str(e)}")
        return error_response("Internal server error", 500)
