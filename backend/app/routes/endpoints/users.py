from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.models.user import UserOut
from app.db.repository.user import get_user
from app.core.responses import success_response, error_response
from app.dependencies.auth import get_current_user

# SH: This is our Main Router for all the routes related to Users
router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)]
)

#SH: Route to get a single user's details
@router.get("/{user_id}", response_model=UserOut)
async def get_user_route(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    #SH: Make sure the user is only accessing their own profile
    if current_user.user_id != user_id:
        return error_response(
            "Unauthorized access",
            http_status=status.HTTP_403_FORBIDDEN
        )
    #SH: Fetch the user from the database
    db_user = await get_user(db, user_id)
    #SH: If the user does not exist in the database
    if not db_user:
        return error_response(
            "User not found",
            http_status=status.HTTP_404_NOT_FOUND
        )
    
    #SH: Convert DB model to response schema and return success response
    user_out = UserOut.model_validate(db_user)
    return success_response("User retrieved successfully", user_out)
