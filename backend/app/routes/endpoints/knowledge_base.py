from fastapi import FastAPI, APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from app.services.knowledge_service import KnowledgeProcessor
from app.db.repository.knowledge_base import create_knowledge_entry as create_knowledge
from app.core.config import settings
from app.db.database import get_db
from app.db.models import User
from app.db.models import KnowledgeBase
from app.dependencies.auth import get_current_user
from app.models.knowledge_base import KnowledgeBaseOut, KnowledgeBaseCreate
from app.core.responses import success_response, error_response
import os
import uuid

#HZ:(Updated) Initialize FastAPI and Router
app = FastAPI()
router = APIRouter(tags=["knowledge"])
processor = KnowledgeProcessor()

@router.get("/knowledge_base")
async def get_knowledge_base(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        # ✅ Ensure user belongs to an organization
        if not current_user.organization_id:
            return error_response("User must belong to an organization", 400)

        # ✅ Fetch knowledge base entries for the user's organization
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.organization_id == current_user.organization_id)
        )
        knowledge_entries = result.scalars().all()

        # ✅ Convert ORM objects to dictionaries
        knowledge_list = [
            {
                "id": entry.id,
                "filename": entry.filename,
                "content_type": entry.content_type,
                "organization_id": entry.organization_id,
                "uploaded_at": entry.uploaded_at.isoformat() if entry.uploaded_at else None,
                "file_size": entry.file_size,
                "chunk_count": entry.chunk_count
            }
            for entry in knowledge_entries
        ]

        return success_response("Knowledge base fetched successfully", knowledge_list)
    except Exception as e:
        return error_response(str(e), 500)

@router.post("/Upload_knowledge_base", response_model=KnowledgeBaseOut)
async def upload_knowledge(
    file: UploadFile = File(...),
    organization_id: int = Form(...),  #HZ:(Updated) Ensure organization_id is received
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    #HZ:(Updated) Ensure user belongs to an organization
    if not current_user.organization_id:
        return error_response("User must belong to an organization to upload KB", 400)

    #HZ:(Updated) Read file content and reset cursor
    content = await file.read()
    file.file.seek(0)
    
    file_size = len(content)
    if file_size > settings.MAX_FILE_SIZE:
        return error_response("File size exceeds 10MB limit", 400)

    #HZ:(Updated) Generate unique filename
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(settings.KNOWLEDGE_DIR, unique_filename)

    #HZ:(Updated) Save file locally
    os.makedirs(settings.KNOWLEDGE_DIR, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        #HZ:(Updated) Process file with LangChain (Ensure organization_id is passed)
        chunk_count = processor.process_file(file_path, file.content_type, organization_id)
        if chunk_count is None:
            raise ValueError("File processing failed")

        #HZ:(Updated) Create database entry
        knowledge_data = KnowledgeBaseCreate(
            filename=unique_filename,
            content_type=file.content_type,
            organization_id=organization_id  # ✅ Include organization_id
        )

        #HZ:(Updated) REMOVE agent_id (Fix the error)
        db_entry = await create_knowledge(
            db=db,
            knowledge_data=knowledge_data,
            file_size=file_size,
            chunk_count=chunk_count
        )

        #HZ:(Updated) Convert the database response to a dictionary (Ensure correct structure)
        if isinstance(db_entry, dict):
            response_data = db_entry  # ✅ Already a dictionary, use directly
        else:
            response_data = {
                "id": db_entry.id,
                "filename": db_entry.filename,
                "content_type": db_entry.content_type,
                "organization_id": db_entry.organization_id,
                "uploaded_at": db_entry.uploaded_at.isoformat() if db_entry.uploaded_at else datetime.utcnow().isoformat(),
                "file_size": db_entry.file_size,
                "chunk_count": db_entry.chunk_count
            }

        #HZ:(Updated) Validate response against KnowledgeBaseOut model
        validated_data = KnowledgeBaseOut.model_validate(response_data)
        return success_response("File uploaded and processed", validated_data)

    except Exception as e:
        #HZ:(Updated) Cleanup file if error occurs
        if os.path.exists(file_path):
            os.remove(file_path)
        return error_response(str(e), 500)

#HZ:(Updated) Include router in the main FastAPI app
app.include_router(router)
