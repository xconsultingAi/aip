from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.repository.organization import create_organization, get_organization, update_organization
from app.models.organization import OrganizationCreate, OrganizationOut, OrganizationUpdate
from app.dependencies.auth import get_current_user

# SH: This is our Main Router for all the routes related to Organization
router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
    dependencies=[Depends(get_current_user)]
)

#SH: Route to create a new organization
@router.post("/", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
async def create_new_organization(
    organization: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    #SH: Save organization in DB
    db_organization = await create_organization(db, organization, current_user.user_id)
    
    #SH: If something went wrong during creation
    if not db_organization:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create organization."
        )

    return db_organization

#SH: Route to fetch a single organization by its id
@router.get("/{organization_id}", response_model=OrganizationOut)
async def read_organization(
    organization_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    #SH: Fetch organization from DB
    db_organization = await get_organization(db, organization_id)

    #SH: If organization does not exist
    if not db_organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found."
        )

    return db_organization

#SH: Route to update an organization
@router.put("/{organization_id}", response_model=OrganizationOut)
async def update_existing_organization(
    organization_id: int,
    organization: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    #SH: Update organization in DB
    updated_organization = await update_organization(
        db, 
        organization_id, 
        organization,
        current_user.user_id
    )
    
    return updated_organization
