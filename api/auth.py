from fastapi import APIRouter
from models.user import CreateUser
from db import get_db
from sqlalchemy import select
from schemas import User



router = APIRouter(prefix="/auth", 
                   tags=["authentification"])


@router.post("/register", response_model = None)
async def register_user(
    user_data: CreateUser
):
    async for db in get_db():
        query = select(User).where(User.username==user_data.username)
        res = await db.execute(query)
        if len(res.scalars().all()) > 0:
            print("alknadsn")
        else:
            print(0)