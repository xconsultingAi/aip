from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.models.user import UserOut
from app.db.repository.user import get_all_users as get_all_users_db
from app.core.responses import success_response
from app.dependencies.auth import get_current_user

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/", response_model=list[UserOut])
async def get_all_users_route(db: AsyncSession = Depends(get_db)): 
    users = await get_all_users_db(db)
    
    users_out = [UserOut.model_validate(user).model_dump() for user in users]
    
    return success_response("Users retrieved successfully", users_out)