import logging
from uuid import UUID

import asyncpg
from fastapi import HTTPException, status

from app.core.security import create_access_token, hash_password, verify_password
from app.schemas.schemas import AuthResponse, LoginRequest, RegisterRequest, UserOut

logger = logging.getLogger(__name__)


async def register_user(req: RegisterRequest, db: asyncpg.Connection) -> AuthResponse:
    # check duplicate email first
    existing = await db.fetchrow("SELECT id FROM users WHERE email = $1", req.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation failed", "fields": {"email": "already in use"}},
        )

    pw_hash = hash_password(req.password)
    new_user = await db.fetchrow(
        "INSERT INTO users (name, email, password) VALUES ($1, $2, $3) "
        "RETURNING id, name, email, created_at",
        req.name, req.email, pw_hash,
    )
    user_out = UserOut(**dict(new_user))
    token = create_access_token(user_out.id, user_out.email)
    logger.info("new user registered", extra={"user_id": str(user_out.id)})
    return AuthResponse(token=token, user=user_out)


async def login_user(req: LoginRequest, db: asyncpg.Connection) -> AuthResponse:
    user_row = await db.fetchrow(
        "SELECT id, name, email, password, created_at FROM users WHERE email = $1",
        req.email,
    )
    # same error for wrong email or wrong password - don't leak which one
    if not user_row or not verify_password(req.password, user_row["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized"},
        )

    user_out = UserOut(
        id=user_row["id"],
        name=user_row["name"],
        email=user_row["email"],
        created_at=user_row["created_at"],
    )
    token = create_access_token(user_out.id, user_out.email)
    logger.info("user logged in", extra={"user_id": str(user_out.id)})
    return AuthResponse(token=token, user=user_out)
