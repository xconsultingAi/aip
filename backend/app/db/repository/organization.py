from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models.organization import Organization
from app.models.organization import OrganizationCreate
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status

async def create_organization(db: AsyncSession, organization: OrganizationCreate, user_id: str):
    try:
        db_organization = Organization(
            name=organization.name, 
            user_id=user_id
        )
        db.add(db_organization)
        await db.commit()
        await db.refresh(db_organization)
        return db_organization
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Organization creation error: {str(e)}"
        )

async def get_organization(db: AsyncSession, organization_id: int):
    result = await db.execute(select(Organization).where(Organization.id == organization_id))
    return result.scalars().first()