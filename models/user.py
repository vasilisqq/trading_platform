from pydantic import BaseModel
# from typing import


class BaseUser(BaseModel):
    email: str
    username: str


class CreateUser(BaseUser):
    password: str


class UserResponse(BaseUser):
    id: str