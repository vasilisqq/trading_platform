from fastapi import APIRouter, Depends
from src.core.dependencies import get_current_user
from src.schemas.user import UserResponse


router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user = Depends(get_current_user)):
    return UserResponse(
        email=current_user.email,
        username=current_user.username,
        id=current_user.id
    )