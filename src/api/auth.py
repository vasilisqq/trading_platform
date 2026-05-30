from fastapi import APIRouter, Depends, Response, Request
from schemas.user import CreateUser, UserResponse, UserLogin
from schemas.token import TokenResponse
from src.core.dependencies import get_user_service
from services.user_service import UserService
from src.core.config import settings
from src.exceptions import TokenNotFoundError
from src.api.utils import set_cookie_refresh_token, build_token_response


router = APIRouter(prefix="/auth", 
                   tags=["authentification"])


@router.post("/register", response_model = TokenResponse)
async def register_user(
    user_data: CreateUser,
    response: Response,
    user_service: UserService = Depends(get_user_service)
):
    data = await user_service.register(user_data)
    set_cookie_refresh_token(response, data["refresh_token"])
    return build_token_response(data["access_token"], data["user"])


@router.post('/login', response_model = TokenResponse)
async def login_user(
    user_data: UserLogin,
    response: Response,
    user_service=Depends(get_user_service)
):
    data = await user_service.login(user_data)
    set_cookie_refresh_token(response, data["refresh_token"])
    return build_token_response(data["access_token"], data["user"])


@router.get("/refresh", response_model=TokenResponse)
async def refresh_token(request: Request,
                        response: Response,
                        user_service: UserService = Depends(get_user_service)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise TokenNotFoundError()
    data = await user_service.refresh(refresh_token)
    set_cookie_refresh_token(response, data["refresh_token"])
    return build_token_response(data["access_token"], data["user"])


@router.post("/logout")
async def logout(request: Request,
                 response: Response,
                 user_service = Depends(get_user_service)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise TokenNotFoundError()
    await user_service.logout(refresh_token)
    response.delete_cookie(key="refresh_token",
                           httponly=True,
                           samesite="lax",
                           secure=True)
    return {"message": "Susssessfully logget out"}




