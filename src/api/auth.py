from fastapi import APIRouter, Depends, Response
from schemas.user import CreateUser, UserResponse, UserLogin
from schemas.token import TokenResponse
from src.core.dependencies import get_user_service
from services.user_service import UserService
from src.core.config import settings


router = APIRouter(prefix="/auth", 
                   tags=["authentification"])


@router.post("/register", response_model = TokenResponse)
async def register_user(
    user_data: CreateUser,
    response: Response,
    user_service: UserService = Depends(get_user_service)
):
    data = await user_service.register(user_data)
    response.set_cookie(
        key="refresh_token",
        value = data["refresh_token"],
        httponly=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        secure=True
    )
    user = data["user"]
    return TokenResponse(
        access_token=data["access_token"],
        user = UserResponse(
            email=user.email,
            username=user.username,
            id=user.id
        )
    )


@router.post('/login', response_model = TokenResponse)
async def login_user(
    user_data: UserLogin,
    response: Response,
    user_service=Depends(get_user_service)
):
    data = await user_service.login(user_data)
    response.set_cookie(
        key="refresh_token",
        value = data["refresh_token"],
        httponly=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        secure=True
    )
    user = data["user"]
    return TokenResponse(
        access_token=data["access_token"],
        user = UserResponse(
            email=user.email,
            username=user.username,
            id=user.id
        )
    )

    

