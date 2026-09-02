from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from uuid import UUID
from zxcvbn import zxcvbn


def validate_password_strength(v):
    result = zxcvbn(v)
    if result['score'] < 3:
        raise ValueError("weak password")
    return v

class BaseUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: EmailStr
    username:str = Field(min_length=3, max_length=50)


class CreateUser(BaseUser):
    password: str = Field(min_length=8, max_length=128)

    @field_validator('password')
    def _strength(cls, v):return validate_password_strength(v)


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
    def _strength(cls, v):return validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator('new_password')
    def _strength(cls, v): return validate_password_strength(v)