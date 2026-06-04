"""Rotas de autenticação admin — multi-tenant com JWT enriquecido."""

import uuid as _uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
import bcrypt as _bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.session import get_db
from app.models.admin_user import AdminUser, AdminRole
from app.models.tenant import Tenant
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse

router = APIRouter()
settings = get_settings()


def create_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def _build_token_payload(user: AdminUser, db: AsyncSession) -> dict:
    """Monta payload JWT com tenant_id, role e branding."""
    payload: dict = {
        "sub": str(user.id),
        "type": "access",
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "email": user.email,
        "full_name": user.full_name,
    }

    if user.tenant_id and user.role != AdminRole.SUPERADMIN:
        payload["tenant_id"] = str(user.tenant_id)

        # Adiciona branding do tenant ao token (evita round-trip no frontend)
        result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
        tenant = result.scalar_one_or_none()
        if tenant and tenant.config:
            branding = tenant.config.get("branding", {})
            payload["branding"] = {
                "cor_primaria": branding.get("cor_primaria", "#1976D2"),
                "cor_secundaria": branding.get("cor_secundaria", "#FFC107"),
                "logo_url": branding.get("logo_url"),
                "tenant_name": tenant.name,
            }
    else:
        # Superadmin
        payload["tenant_id"] = None
        payload["branding"] = {
            "cor_primaria": "#1A1A2E",
            "cor_secundaria": "#E94560",
            "logo_url": None,
            "tenant_name": "Atendê Platform",
        }

    return payload


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(AdminUser).where(AdminUser.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not _bcrypt.checkpw(body.password.encode(), user.hashed_password.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo.",
        )

    access_payload = await _build_token_payload(user, db)
    access_token = create_token(
        access_payload,
        timedelta(minutes=settings.jwt_access_expire_minutes),
    )

    refresh_token = create_token(
        {"sub": str(user.id), "type": "refresh"},
        timedelta(days=settings.jwt_refresh_expire_days),
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        payload = jwt.decode(
            body.refresh_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")

    user_id = payload.get("sub")
    try:
        user_uuid = _uuid.UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")

    result = await db.execute(select(AdminUser).where(AdminUser.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inválido.")

    access_payload = await _build_token_payload(user, db)
    access_token = create_token(
        access_payload,
        timedelta(minutes=settings.jwt_access_expire_minutes),
    )
    new_refresh = create_token(
        {"sub": str(user.id), "type": "refresh"},
        timedelta(days=settings.jwt_refresh_expire_days),
    )

    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.get("/me")
async def get_me(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Retorna dados do usuário logado + config do tenant.
    Usa o dependency get_current_admin via middleware — importado aqui para evitar circular.
    """
    from app.api.middleware.auth import get_current_admin
    from fastapi import Request
    # Esta rota é wrapper — o middleware injeta o usuário
    # O endpoint real está em middleware/auth.py como dependency
    raise HTTPException(status_code=501, detail="Use o middleware diretamente.")
