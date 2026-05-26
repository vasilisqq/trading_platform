from fastapi import APIRouter, HTTPException, Depends
from schemas.user import CreateUser
from schemas.token import TokenResponse
from src.core.dependencies import get_user_service
from services.user_service import UserService


router = APIRouter(prefix="/auth", 
                   tags=["authentification"])


@router.post("/register", response_model = TokenResponse)
async def register_user(
    user_data: CreateUser,
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.register(user_data)
