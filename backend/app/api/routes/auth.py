"""Rotas de autenticação admin."""
import bcrypt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.database.session import get_db
from app.models.admin_user import AdminUser
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse

router = APIRouter()
settings = get_settings()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(AdminUser).where(AdminUser.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha incorretos.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inativo.")
    access_token = create_token(
        {"sub": str(user.id), "email": user.email, "type": "access"},
        timedelta(minutes=settings.jwt_access_expire_minutes)
    )
    refresh_token = create_token(
        {"sub": str(user.id), "email": user.email, "type": "refresh"},
        timedelta(days=settings.jwt_refresh_expire_days)
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        payload = jwt.decode(body.refresh_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")
        result = await db.execute(select(AdminUser).where(AdminUser.email == payload.get("email")))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inativo.")
        access_token = create_token(
            {"sub": str(user.id), "email": user.email, "type": "access"},
            timedelta(minutes=settings.jwt_access_expire_minutes)
        )
        refresh_token = create_token(
            {"sub": str(user.id), "email": user.email, "type": "refresh"},
            timedelta(days=settings.jwt_refresh_expire_days)
        )
        return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")
