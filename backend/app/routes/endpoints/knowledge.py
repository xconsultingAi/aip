from fastapi import APIRouter, UploadFile, File, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.knowledge import KnowledgeBaseCreate, KnowledgeBaseOut
from app.db.repository.knowledge import create_knowledge
from app.core.responses import success_response
from app.models.user import UserOut as User

router = APIRouter(tags=["knowledge"])

@router.post("/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    organization_id: int = Form(...),  
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # File validation
    knowledge_data = KnowledgeBaseCreate(
        filename=file.filename,
        content_type=file.content_type,
        organization_id=organization_id
    )
    db_knowledge = await create_knowledge(db, knowledge_data)
    return success_response("File uploaded", KnowledgeBaseOut.model_validate(db_knowledge))
