from pydantic import BaseModel, Field

#SH: These are Pydanitc Models used for request & response validation
class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Organization name is compulsory")

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(OrganizationBase):
    pass

class OrganizationOut(OrganizationBase):
    id: int
    user_id: str

    class Config:
        from_attributes = True