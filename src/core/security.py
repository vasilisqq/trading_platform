import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from src.core.config import settings
import hashlib
import uuid


def hash_password(password: str) -> str:
    combined = password.encode()
    hash256 = hashlib.sha256(combined).digest()
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(hash256, salt)
    return hashed.decode()


def _create_token(token_type: str, data: dict) -> str:
    to_encode = data.copy()
    if token_type == "refresh":
        expire = datetime.now(tz=timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"})
    elif token_type == "access":
        jti = uuid.uuid7()
        expire = datetime.now(tz=timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "jti": str(jti), "type": "access"})
    else:
        raise ValueError(f"unknown token type f{token_type}")
    return jwt.encode(to_encode, settings.SECRET_KEY.get_secret_value(), algorithm="HS256")


def create_access_token(data: dict) -> str:
    return _create_token("access", data)


def create_refresh_token(data:dict) -> str:
    return _create_token("refresh", data)


def verify_password(password: str, hashed_password: str) -> bool:
    combined = password.encode()
    hash256 = hashlib.sha256(combined).digest()
    return bcrypt.checkpw(hash256, hashed_password.encode())


def _decode_token(token:str, verify_exp:bool) -> dict:
    options = {"verify_exp": verify_exp}
    return jwt.decode(
        token,
        settings.SECRET_KEY.get_secret_value(),
        algorithms=["HS256"],
        options=options
    )


def decode_refresh_token(token: str, verify_exp: bool = True) -> dict:
    payload = _decode_token(token, verify_exp=verify_exp)
    if payload.get("type") != "refresh":
        raise jwt.InvalidTokenError("Not an refresh token")
    return payload


def decode_access_token(token: str, verify_exp: bool = True) -> dict:
    payload = _decode_token(token, verify_exp=verify_exp)
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Not an access token")
    return payload