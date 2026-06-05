from fastapi import APIRouter, Depends, Response, Request, Query, Body
from fastapi.security import HTTPAuthorizationCredentials
from src.schemas.user import CreateUser, UserLogin, ForgotPasswordRequest, ResetPasswordRequest
from src.schemas.token import TokenResponse
from src.core.dependencies import get_user_service
from src.services.user_service import UserService
from src.exceptions import TokenNotFoundError
from src.api.utils import set_cookie_refresh_token, build_token_response
from src.core.dependencies import security


router = APIRouter(prefix="/auth", 
                   tags=["authentification"])


@router.post("/register")
async def register_user(
    user_data: CreateUser,
    user_service: UserService = Depends(get_user_service)
):
    await user_service.register(user_data)
    return {"Register": "Email was sent"}


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
                 user_service = Depends(get_user_service),
                 credentials: HTTPAuthorizationCredentials = Depends(security)):
    refresh_token = request.cookies.get("refresh_token")
    print(refresh_token)
    if not refresh_token:
        raise TokenNotFoundError()
    
    access_token = credentials.credentials
    print(access_token)
    await user_service.logout(refresh_token, access_token)
    response.delete_cookie(key="refresh_token",
                           httponly=True,
                           samesite="lax",
                           secure=True)
    return {"message": "Successfully logget out"}


@router.get("/verify-email", response_model=TokenResponse)
async def verify_email(token: str, 
                       response: Response,
                       user_service: UserService = Depends(get_user_service)):
    data = await user_service.verify_email(token)
    set_cookie_refresh_token(response, data["refresh_token"])
    return build_token_response(data["access_token"], data["user"])

@router.post("/forgot_password")
async def forgot_password(
    data: ForgotPasswordRequest,
    user_service: UserService = Depends(get_user_service) 
):
    await user_service.forgot_password(data.email)
    return {"message": "check your email"}
    

@router.post("/reset-password")
async def reset_password(
    new_password: ResetPasswordRequest,
    token:str = Query(...),
    user_service: UserService = Depends(get_user_service) 
):
    return await user_service.reset_password(token, new_password.password)
