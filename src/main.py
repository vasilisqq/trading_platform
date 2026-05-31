from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.exceptions import UserAlreadyExistsError, DataBaseError, UserNotFoundError, UserDisabledError, TokenNotFoundError
import uvicorn
from src.core.config import settings
from api import router
from contextlib import asynccontextmanager
from src.core.redis import get_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_redis()
    yield
    await close_redis()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)


@app.exception_handler(UserAlreadyExistsError)
async def user_exists_handler(request: Request, exc: UserAlreadyExistsError):
    return JSONResponse(
        status_code=409,
        content={"detail": f"User with this {exc.field} already exists"},
    )

@app.exception_handler(DataBaseError)
async def database_error_handler(request: Request, exc: DataBaseError):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Error with creating new {exc.table_name}"},
    )

@app.exception_handler(UserNotFoundError)
async def user_not_found_handler(request: Request, exc: UserNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": "User does not exists"},
    )


@app.exception_handler(UserDisabledError)
async def user_disabled_handler(request: Request, exc: UserDisabledError):
    return JSONResponse(
        status_code=403,
        content={"detail": "User was blocked"},
    )


@app.exception_handler(TokenNotFoundError)
async def token_not_found_handler(request: Request, exc: TokenNotFoundError):
    return JSONResponse(
        status_code=401,
        content={"detail": "Refresh token not found"},
    )



app.include_router(router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
