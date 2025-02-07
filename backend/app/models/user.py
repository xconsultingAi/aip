from pydantic import BaseModel

#MJ: These are Pydantic Models used for Request & Response Validation

class UserBase(BaseModel):
    user_id: str

# Response model for User
class UserOut(UserBase):
    id: int
    organization_id: int | None = None 

    class Config:
        from_attributes = True
