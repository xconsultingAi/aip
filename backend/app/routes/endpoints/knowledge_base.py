import logging
from fastapi import APIRouter, Body, Form, HTTPException, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.db.database import get_db
from app.db.models.user import User
from app.db.models.knowledge_base import KnowledgeBase
from app.services.knowledge_service import process_file, process_url
from app.db.repository.knowledge_base import create_knowledge_entry
from app.dependencies.auth import get_current_user
from app.models.knowledge_base import KnowledgeBaseOut, KnowledgeBaseCreate, KnowledgeFormatCount, KnowledgeURL, OrganizationKnowledgeCount
from app.core.responses import success_response, error_response
import os
import uuid
from pathlib import Path

# SH: This is our Main Router for all the routes related to Knowledge base
router = APIRouter(tags=["knowledge"])
logger = logging.getLogger(__name__)

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

    # Validate file extension matches selected format
    file_extension = Path(file.filename).suffix.lstrip('.').lower()
    if file_extension != kb_format.lower():
        return error_response(
            f"Selected format '{kb_format}' does not match uploaded file extension '.{file_extension}'",
            400
        )

    #SH: Read file content and reset cursor
    try:
        content = await file.read()
        file.file.seek(0)
        file_size = len(content)

        if file_size > settings.MAX_FILE_SIZE:
            return error_response("File size exceeds 10MB limit", 400)

        #SH: Unique filename
        ext = Path(file.filename).suffix
        unique_id = uuid.uuid4().hex[:8]
        unique_filename = f"{unique_id}{ext}"
        file_path = os.path.join(settings.KNOWLEDGE_DIR, unique_filename)

        #SH: Save file
        os.makedirs(settings.KNOWLEDGE_DIR, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(content)

        #SH: Process file with organization_id
        chunk_count = process_file(file_path, file.content_type, current_user.organization_id)
        if chunk_count is None:
            raise ValueError("File processing failed")

        #SH: Create database entry
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
            chunk_count=chunk_count
        )
        return success_response(
            "File uploaded and processed",
            KnowledgeBaseOut.model_validate(db_entry)
        )

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        # Cleanup file if it exists
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return error_response(str(e), 500)



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

@router.get("/org_knowledge_count", response_model=OrganizationKnowledgeCount)
async def get_organization_knowledge_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get count of knowledge bases for the current user's organization
    """
    # SH: Ensure user belongs to an organization
    if not current_user.organization_id:
        return error_response("User must belong to an organization", 400)
    
    try:
        # Import the repository function explicitly to avoid naming conflicts
        from app.db.repository.knowledge_base import get_organization_knowledge_count as repo_count
        count = await repo_count(db, current_user.organization_id)
        
        return {
            "organization_id": current_user.organization_id,
            "total_knowledge_bases": count
        }
    except Exception as e:
        logger.error(f"Error getting knowledge base count: {str(e)}")
        return error_response("Could not retrieve knowledge base count", 500)

#Route for Url Scraping
@router.post("/add_url", responses={
    400: {"model": error_response, "description": "Invalid URL or scraping failed"},
    429: {"model": error_response, "description": "Rate limit exceeded"}
})
async def add_knowledge_from_url(
    url_data: KnowledgeURL = Body(..., description="URL and scraping options"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Add knowledge from URL with:
    # - Automatic content extraction
    # - Robots.txt compliance
    # - Rate limiting
    
    if not current_user.organization_id:
        raise HTTPException(400, "User organization not set")

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
@router.get("/knowledge_base/{kb_id}/agent_count")
async def get_knowledge_agent_count(
    kb_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.organization_id:
        return error_response("User must belong to an organization", 400)
    
    try:
        from app.db.repository.knowledge_base import get_agent_count_for_knowledge
        count = await get_agent_count_for_knowledge(db, kb_id, current_user.organization_id)
        return success_response(
            "Agent count retrieved",
            {"agent_count": count}
        )
    except HTTPException as e:
        return error_response(e.detail, e.status_code)
    except Exception as e:
        logger.error(f"Error getting agent count: {str(e)}", exc_info=True)
        return error_response("Internal server error", 500)

# Route for format count
@router.get("/format_count", response_model=list[KnowledgeFormatCount])
async def get_knowledge_format_counts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get count of knowledge bases grouped by file format for the organization
    # Returns: List of objects with format and count
    
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