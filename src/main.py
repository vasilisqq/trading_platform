from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.exceptions import UserAlreadyExistsError
import uvicorn
from src.core.config import settings
from api import router


app = FastAPI(title=settings.APP_NAME)


@app.exception_handler(UserAlreadyExistsError)
async def user_exists_handler(request: Request, exc: UserAlreadyExistsError):
    return JSONResponse(
        status_code=409,
        content={f"detail:User with this {exc.field} already exists"},
    )


app.include_router(router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
