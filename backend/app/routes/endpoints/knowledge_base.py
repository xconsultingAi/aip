from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.db.database import get_db
from app.db.models import User
from app.db.models.knowledge_base import KnowledgeBase 
from app.services.knowledge_service import process_file
from app.db.repository.knowledge_base import create_knowledge_entry
from app.dependencies.auth import get_current_user
from app.models.knowledge_base import KnowledgeBaseOut, KnowledgeBaseCreate
from app.core.responses import success_response, error_response
import os
import uuid
from PyPDF2 import PdfReader  # type: ignore

# SH: This is our Main Router for all the routes related to Knowledge base
router = APIRouter(tags=["knowledge"])

@router.post("/upload_knowledge_base", response_model=KnowledgeBaseOut)
async def upload_knowledge(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    #SH: Ensure user belongs to an organization
    if not current_user.organization_id:
        return error_response("User must belong to an organization to upload KB", 400)

    #SH: Read file content and reset cursor
    content = await file.read()
    file.file.seek(0)
    file_size = len(content)

    if file_size > settings.MAX_FILE_SIZE:
        return error_response("File size exceeds 10MB limit", 400)

    #SH: Unique filename
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(settings.KNOWLEDGE_DIR, unique_filename)

    #SH: Save file
    os.makedirs(settings.KNOWLEDGE_DIR, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)

    #SH: Verify file path
    if not os.path.exists(file_path):
        return error_response("File was not saved correctly", 500)

    try:
        #SH: Process file based on content type
        if file.content_type == "application/pdf":
            #SH: Extract text from PDF
            reader = PdfReader(file_path)
            file_content = ""
            for page in reader.pages:
                file_content += page.extract_text()
        else:
            #SH: For text files, read directly
            with open(file_path, "r", encoding="utf-8") as f:
                file_content = f.read()

        #SH: Process file with organization_id
        chunk_count = process_file(file_path, file.content_type, current_user.organization_id)
        if chunk_count is None:
            raise ValueError("File processing failed")

        #SH: Create database entry
        knowledge_data = KnowledgeBaseCreate(
            filename=unique_filename,
            content_type=file.content_type,
            organization_id=current_user.organization_id
        )

        db_entry = await create_knowledge_entry(
            db=db,
            knowledge_data=knowledge_data,
            file_size=file_size,
            chunk_count=chunk_count
        )

        #SH: Convert db_entry to dictionary (if it isn't already)
        if not isinstance(db_entry, dict):
            db_entry = {
                "id": db_entry.id,
                "filename": db_entry.filename,
                "content_type": db_entry.content_type,
                "organization_id": db_entry.organization_id,
                "uploaded_at": db_entry.uploaded_at.isoformat(),
                "file_size": db_entry.file_size,
                "chunk_count": db_entry.chunk_count
            }

        #SH: Validate the response against the KnowledgeBaseOut model
        validated_data = KnowledgeBaseOut.model_validate(db_entry)
        return success_response("File uploaded and processed", validated_data)

    except Exception as e:
        #SH: Cleanup file if error occurs
        if os.path.exists(file_path):
            os.remove(file_path)
        return error_response(str(e), 500)

# Route for get all KBs from database    
@router.get("/knowledge_base", response_model=list[KnowledgeBaseOut])
async def get_all_knowledge_bases(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeBase))
    knowledge_bases = result.scalars().all()
    return success_response(
        "Knowledge bases retrieved",
        [KnowledgeBaseOut.model_validate(kb.__dict__) for kb in knowledge_bases]
    )
