from fastapi import APIRouter, HTTPException, Depends
from schemas.user import CreateUser
from src.core.dependencies import get_user_service
from services.user_service import UserService


router = APIRouter(prefix="/auth", 
                   tags=["authentification"])


@router.post("/register", response_model = None)
async def register_user(
    user_data: CreateUser,
    user_service: UserService = Depends(get_user_service)
):
    if await user_service.get_user_by_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email already exists")
    if user_service.get_user_by_username(user_data.username):
        raise HTTPException(status_code=400, detail="username already exists")
    print(1)
