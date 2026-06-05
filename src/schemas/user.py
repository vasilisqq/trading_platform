from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from uuid import UUID
from zxcvbn import zxcvbn


class BaseUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: EmailStr
    username:str = Field(min_length=3, max_length=50)


class CreateUser(BaseUser):
    password: str = Field(min_length=8, max_length=128)

    @field_validator('password')
    def validate_password(cls, v):
        result = zxcvbn(v)
        if result['score'] < 3:
            raise ValueError("weak password")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseUser):
    id: UUID


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    @field_validator('password')
    def validate_password(cls, v):
        result = zxcvbn(v)
        if result['score'] < 3:
            raise ValueError("weak password")
        return v

