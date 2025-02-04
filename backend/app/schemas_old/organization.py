from pydantic import BaseModel, Field

#SH: Schema for creating an organization
class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Organization name must be a valid string.")

#SH: Schema for returning organization data
class OrganizationOut(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True
