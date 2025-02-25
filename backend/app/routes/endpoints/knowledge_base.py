from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.database import get_db
from app.services.knowledge_service import KnowledgeProcessor
from app.db.repository.knowledge_base import create_knowledge_entry as create_knowledge
from app.dependencies.auth import get_current_user
from app.models.knowledge_base import KnowledgeBaseOut, KnowledgeBaseCreate
from app.core.responses import success_response, error_response
import os
import uuid
from datetime import datetime

router = APIRouter(tags=["knowledge"])
processor = KnowledgeProcessor()

@router.post("/upload", response_model=KnowledgeBaseOut)
async def upload_knowledge(
    file: UploadFile = File(...),
    organization_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # ✅ Ensure content type exists
    if not file.content_type or file.content_type not in settings.ALLOWED_CONTENT_TYPES:
        return error_response("Invalid or missing file type", 400)

    # ✅ Read file content and reset cursor
    content = await file.read()
    file.file.seek(0)  # Reset file cursor
    file_size = len(content)

    if file_size > settings.MAX_FILE_SIZE:
        return error_response("File size exceeds 10MB limit", 400)

    # ✅ Ensure unique filename
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(settings.KNOWLEDGE_DIR, unique_filename)

    # ✅ Save file
    os.makedirs(settings.KNOWLEDGE_DIR, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        # ✅ Process file with LangChain
        chunk_count = processor.process_file(file_path, file.content_type)

        if chunk_count is None:
            raise ValueError("File processing failed")

        # ✅ Create database entry
        knowledge_data = KnowledgeBaseCreate(
            filename=unique_filename,
            content_type=file.content_type,
            organization_id=organization_id
        )

        db_entry = await create_knowledge(
            db=db,
            knowledge_data=knowledge_data,
            file_size=file_size,
            chunk_count=chunk_count,
            agent_id=None,
            knowledge_ids=[]
        )

        # ✅ Convert db_entry to dictionary safely
        if isinstance(db_entry, dict):
            db_entry_dict = db_entry
        else:
            db_entry_dict = {column: getattr(db_entry, column) for column in db_entry.__table__.columns.keys()}

        # ✅ Ensure uploaded_at is always valid
        uploaded_at_value = db_entry_dict.get("uploaded_at", None)
        if uploaded_at_value is None:
            uploaded_at_value = datetime.utcnow()  # Default if None

        # ✅ Convert datetime to string format
        uploaded_at_str = uploaded_at_value.isoformat() if isinstance(uploaded_at_value, datetime) else str(uploaded_at_value)

        # ✅ Convert the response to match the KnowledgeBaseOut model
        response_data = {
            "id": db_entry_dict["id"],
            "filename": db_entry_dict["filename"],
            "content_type": db_entry_dict["content_type"],
            "organization_id": db_entry_dict["organization_id"],
            "uploaded_at": uploaded_at_str,
            "file_size": db_entry_dict["file_size"],
            "chunk_count": db_entry_dict["chunk_count"]
        }

        # ✅ Validate the response against the KnowledgeBaseOut model
        validated_data = KnowledgeBaseOut.model_validate(response_data)
        return success_response("File uploaded and processed", validated_data)

    except Exception as e:
        # ✅ Cleanup file if error occurs
        if os.path.exists(file_path):
            os.remove(file_path)
        return error_response(str(e), 500)
