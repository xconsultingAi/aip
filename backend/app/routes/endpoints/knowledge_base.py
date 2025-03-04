from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.db.database import get_db
from app.db.models.knowledge_base import KnowledgeBase 
from app.services.knowledge_service import process_file
from app.db.repository.knowledge_base import create_knowledge_entry
from app.dependencies.auth import get_current_user
from app.models.knowledge_base import KnowledgeBaseOut, KnowledgeBaseCreate
from app.core.responses import success_response, error_response
import os
import uuid
from datetime import datetime, timezone
from PyPDF2 import PdfReader

router = APIRouter(tags=["knowledge"])

@router.post("/Upload_knowledge_base", response_model=KnowledgeBaseOut)
async def upload_knowledge(
    file: UploadFile = File(...),
    organization_id: int = Form(...),
    agent_id: int = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not file.content_type or file.content_type not in settings.ALLOWED_CONTENT_TYPES:
        return error_response("Invalid or missing file type", 400)

    # Read file content and reset cursor
    content = await file.read()
    file.file.seek(0)
    file_size = len(content)

    if file_size > settings.MAX_FILE_SIZE:
        return error_response("File size exceeds 10MB limit", 400)

    #unique filename
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(settings.KNOWLEDGE_DIR, unique_filename)

    # Save file
    os.makedirs(settings.KNOWLEDGE_DIR, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)

    # Verify file path
    if not os.path.exists(file_path):
        return error_response("File was not saved correctly", 500)

    try:
        # Process file based on content type
        if file.content_type == "application/pdf":
            # Extract text from PDF
            reader = PdfReader(file_path)
            file_content = ""
            for page in reader.pages:
                file_content += page.extract_text()
        else:
            # For text files, read directly
            with open(file_path, "r", encoding="utf-8") as f:
                file_content = f.read()

        # Process file
        chunk_count = process_file(file_path, file.content_type)
        if chunk_count is None:
            raise ValueError("File processing failed")

        # Create database entry
        knowledge_data = KnowledgeBaseCreate(
            filename=unique_filename,
            content_type=file.content_type,
            organization_id=organization_id
        )

        db_entry = await create_knowledge_entry(
            db=db,
            knowledge_data=knowledge_data,
            file_size=file_size,
            chunk_count=chunk_count,
            agent_id=agent_id,
            knowledge_ids=[]
        )

        # Convert db_entry to dictionary
        if isinstance(db_entry, dict):
            db_entry_dict = db_entry
        else:
            db_entry_dict = {column: getattr(db_entry, column) for column in db_entry.__table__.columns.keys()}

        # ISO formatted string with timezone info
        uploaded_at_value = db_entry_dict.get("uploaded_at", None)
        if not uploaded_at_value:
            uploaded_at_str = datetime.now(timezone.utc).isoformat()
        elif isinstance(uploaded_at_value, datetime):
            # datetime is timezone aware
            if uploaded_at_value.tzinfo is None:
                uploaded_at_str = uploaded_at_value.replace(tzinfo=timezone.utc).isoformat()
            else:
                uploaded_at_str = uploaded_at_value.astimezone(timezone.utc).isoformat()
        elif isinstance(uploaded_at_value, str):
            try:
                dt = datetime.fromisoformat(uploaded_at_value)
                # Ensure dt is timezone aware
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                uploaded_at_str = dt.isoformat()
            except ValueError:
                uploaded_at_str = datetime.now(timezone.utc).isoformat()
        else:
            uploaded_at_str = datetime.now(timezone.utc).isoformat()

        # Convert the response to match the KnowledgeBaseOut model
        response_data = {
            "id": db_entry_dict["id"],
            "filename": db_entry_dict["filename"],
            "content_type": db_entry_dict["content_type"],
            "organization_id": db_entry_dict["organization_id"],
            "uploaded_at": uploaded_at_str,
            "file_size": db_entry_dict["file_size"],
            "chunk_count": db_entry_dict["chunk_count"]
        }

        # Validate the response against the KnowledgeBaseOut model
        validated_data = KnowledgeBaseOut.model_validate(response_data)
        return success_response("File uploaded and processed", validated_data)

    except Exception as e:
        # Cleanup file if error occurs
        if os.path.exists(file_path):
            os.remove(file_path)
        return error_response(str(e), 500)
@router.get("/knowledge_base", response_model=list[KnowledgeBaseOut])
async def get_all_knowledge_bases(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeBase))
    knowledge_bases = result.scalars().all()
    return success_response(
        "Knowledge bases retrieved",
        [KnowledgeBaseOut.model_validate(kb.__dict__) for kb in knowledge_bases]
    )
