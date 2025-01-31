from pydantic import BaseModel

#MJ: These are Pydanitc Models used for Request & Response Validation

class UserBase(BaseModel):
    user_id: str
    

class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True 
