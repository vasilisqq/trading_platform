from fastapi import APIRouter, Depends, Response, Request, Query, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from src.schemas.user import CreateUser, UserLogin, ForgotPasswordRequest, ResetPasswordRequest
from src.schemas.token import TokenResponse
from src.core.dependencies import get_user_service, get_google_oauth
from src.services.user_service import UserService
from src.exceptions import TokenNotFoundError
from src.api.utils import set_cookie_refresh_token, build_token_response
from src.core.dependencies import security
from uuid import uuid4
from src.services.google_oauth import GoogleOAuthService
from fastapi import BackgroundTasks
from src.exceptions import UserNotFoundError


router = APIRouter(prefix="/auth", 
                   tags=["authentification"])


@router.post("/register")
async def register_user(
    user_data: CreateUser,
    background_tasks: BackgroundTasks,
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.register(user_data)
    background_tasks.add_task(
        user_service.email_verification.send_email_register,
        user.email, 
        user.id
    )
    return {"Register": "Email was sent"}

@router.post("/resend-verification")
async def resend_verification(
    email: str,
    background_tasks: BackgroundTasks,
    user_service: UserService = Depends(get_user_service),
    
):
    user = await user_service.get_user_by_email(email)
    if not user or user.email_verified:
        raise UserNotFoundError()
    
    background_tasks.add_task(
        user_service.email_verification.send_email_register,
        user.email,
        user.id
    )
    return {"message": "Email was sent"}

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


@router.get("/google")
async def google_auth(
    response: Response,
    oauth: GoogleOAuthService = Depends(get_google_oauth)
):
    state = str(uuid4())
    url = await oauth.get_auth_url(state)
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600
    )
    return {"auth_url": url}


@router.get("/google/callback")
async def google_callback(
    response: Response,
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    user_service: UserService = Depends(get_user_service)
):
    cookie_state = request.cookies.get("oauth_state")
    if not cookie_state or cookie_state != state:
        raise HTTPException(400, "Invalid state")
    response.delete_cookie("oauth_state")
    data = await user_service.google_auth(code, state)
    set_cookie_refresh_token(response, data["refresh_token"])
    return build_token_response(data["access_token"], data["user"])