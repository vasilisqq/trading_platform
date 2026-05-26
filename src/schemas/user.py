from pydantic import BaseModel
from uuid import UUID

class BaseUser(BaseModel):
    email: str
    username: str


class CreateUser(BaseUser):
    password: str


class UserResponse(BaseUser):
    id: UUID