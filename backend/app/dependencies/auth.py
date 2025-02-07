from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import verify_clerk_token
from app.db.repository.user import get_user, create_user
from app.db.repository.organization import create_organization
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.organization import OrganizationCreate
from app.db.models.user import User

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
    #TODO: MJ: This needs to be optimzied. We should not be hitting the database for every request
    #SH: Create a Default Organization for new users
    user = await get_user(db, user_id)
    if not user:
        #SH: Create user if not found
        user = await create_user(db, user_id=user_id)
        
        #SH: Create default organization for the new user
        org_name = f"{user.name}'s Organization" if user.name else "My Organization"
        org_data = OrganizationCreate(name=org_name)
        organization = await create_organization(db, org_data, user_id)
        
        #SH: Link user to the organization
        user.organization_id = organization.id
        await db.commit()
        await db.refresh(user)
    
    #SH: For existing users without organization (backward compatibility)
    if not user.organization_id:
        org_data = OrganizationCreate(name="Recovery Organization")
        organization = await create_organization(db, org_data, user_id)
        user.organization_id = organization.id
        await db.commit()
        await db.refresh(user)

    return user 
