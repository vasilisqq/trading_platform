from fastapi import Response
from src.core.config import settings
from src.schemas.token import TokenResponse
from src.schemas.user import UserResponse
from src.models.user import User


def set_cookie_refresh_token(response: Response, refresh_token:str) -> None:
    response.set_cookie(
        key="refresh_token",
        value = refresh_token,
        httponly=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        secure=True
    )

def build_token_response(access_token: str, user:User) -> TokenResponse:
    return TokenResponse(
        access_token=access_token,
        user = UserResponse.model_validate(user)
    )
    