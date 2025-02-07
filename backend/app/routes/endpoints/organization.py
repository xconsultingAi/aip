from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.repository.organization import create_organization, get_organization
from app.models.organization import OrganizationCreate, OrganizationOut
from app.dependencies.auth import get_current_user
from app.core.responses import success_response, error_response 

router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
    dependencies=[Depends(get_current_user)]  # Secure routes
)

@router.post("/", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
async def create_new_organization(
    organization: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user) 
):
    # creating organization and link to the user
    db_organization = await create_organization(db, organization, current_user.user_id)

    current_user.organization_id = db_organization.id
    await db.commit()

    return db_organization

@router.get("/{organization_id}", response_model=OrganizationOut)
async def read_organization(
    organization_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_organization = await get_organization(db, organization_id)
    if not db_organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found."
        )
    return db_organization
