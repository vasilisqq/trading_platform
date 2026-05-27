from pydantic import BaseModel, EmailStr, Field
from uuid import UUID

class BaseUser(BaseModel):
    email: EmailStr
    username:str = Field(min_length=3, max_length=50)


class CreateUser(BaseUser):
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseUser):
    id: UUID

    class Config:
        from_attributes = True