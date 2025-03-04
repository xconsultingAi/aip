from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import verify_clerk_token
from app.db.repository.user import get_user, create_user
from app.db.repository.organization import create_organization
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.organization import OrganizationCreate
from app.db.models.user import User
from typing import List

http_bearer = HTTPBearer()

#MJ: This is our Main Dependecy for all the routes that require Authentication. 
#MJ: It will return the current user based on the token provided in the request.
#MJ: It will also create a new user if the user is not found in the database
#MJ: This is a very basic implementation. We need to add more security checks
#MJ: (e.g. Roles and Permissions) in the future

async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
        db: AsyncSession = Depends(get_db)
) -> User:
    payload = verify_clerk_token(credentials)
    user_id = payload.get("sub")

    #TODO: MJ: Add additional security checks (e.g. Roles and Permissions)
    print(f"User ID: {user_id}")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )
    #TODO:MJ: This needs to be optimized. We should not be hitting the database for every request
    user = await get_user(db, user_id)
    
    if not user:
        user = await create_user(
            db, 
            user_id=user_id,
            name=payload.get("username"),
            email=payload.get("email"), 
            organization_id=None 
        )  
        await db.refresh(user)
        
    # if not user.organization_id:
    #     raise HTTPException(
    #         status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    #         detail="User has no organization. Redirect to organization creation page.",
    #         headers={"Location": "/create-organization"}
    #     )
    return user

async def validate_knowledge_access(
    knowledge_ids: List[int],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check user has access to all knowledge bases
    pass