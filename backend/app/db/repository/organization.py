from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models.organization import Organization
from app.models.organization import OrganizationCreate, OrganizationUpdate
from app.db.repository.user import get_user 
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status

# SH: This file will contain all the database operations related to the Organization model

# SH: Create a new organization and assign it to the user
async def create_organization(db: AsyncSession, organization: OrganizationCreate, user_id: str):
    try:
        db_organization = Organization(
            name=organization.name, 
            user_id=user_id
        )
        # SH: Add the organization to the session and commit to the database
        db.add(db_organization)
        await db.commit()
        await db.refresh(db_organization)
        # SH: Retrieve the user and associate the new organization
        user = await get_user(db, user_id)
        if user:
            user.organization_id = db_organization.id
            await db.commit()
        
        # SH: Return the created organization object
        return db_organization

    except SQLAlchemyError as e:
        # SH: If any database error occurs raise HTTPException
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Organization creation error: {str(e)}"
        )

# SH: Retrieve a specific organization by its Id
async def get_organization(db: AsyncSession, organization_id: int):
    result = await db.execute(select(Organization).where(Organization.id == organization_id))

    return result.scalars().first()

# SH: Update an existing organization
async def update_organization(
    db: AsyncSession, 
    organization_id: int, 
    organization: OrganizationUpdate,
    current_user_id: str
):
    try:
        #SH: Get the organization from database
        result = await db.execute(select(Organization).where(Organization.id == organization_id))
        db_organization = result.scalars().first()
        
        if not db_organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found."
            )
            
        #SH: Check if the current user owns the organization
        if db_organization.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this organization."
            )
            
        #SH: Update the organization fields
        db_organization.name = organization.name
        
        await db.commit()
        await db.refresh(db_organization)
        
        return db_organization
        
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Organization update error: {str(e)}"
        )