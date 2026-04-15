from fastapi import APIRouter, Depends
from asyncpg import Connection

from app.db.database import get_db
from app.schemas.schemas import AuthResponse, LoginRequest, RegisterRequest
from app.services import auth_service

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(req: RegisterRequest, db: Connection = Depends(get_db)):
    return await auth_service.register_user(req, db)


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, db: Connection = Depends(get_db)):
    return await auth_service.login_user(req, db)
