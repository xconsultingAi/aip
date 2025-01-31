from pydantic import BaseModel

#SH: These are Pydanitc Models used for request & response validation
class OrganizationBase(BaseModel):
    name: str 

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationOut(OrganizationBase):
    id: int 
    user_id: str 

    class Config:
        from_attributes = True