"""Middleware de autenticação JWT — multi-tenant com role-based access."""

from __future__ import annotations

import uuid as _uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.session import get_db
from app.models.admin_user import AdminRole, AdminUser

security = HTTPBearer()
settings = get_settings()


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    """Valida JWT e retorna o AdminUser autenticado (qualquer role)."""
    token = credentials.credentials

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")

    try:
        user_uuid = _uuid.UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")

    result = await db.execute(select(AdminUser).where(AdminUser.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado."
        )

    return user


async def get_current_superadmin(
    user: AdminUser = Depends(get_current_admin),
) -> AdminUser:
    """Dependency: exige role superadmin."""
    if user.role != AdminRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a superadmins.",
        )
    return user


async def get_current_tenant_admin(
    user: AdminUser = Depends(get_current_admin),
) -> AdminUser:
    """Dependency: exige role tenant_admin ou superadmin."""
    if user.role not in (AdminRole.TENANT_ADMIN, AdminRole.SUPERADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a admins de tenant.",
        )
    return user


def get_tenant_id_from_user(user: AdminUser) -> _uuid.UUID | None:
    """
    Extrai o tenant_id do usuário.
    Superadmin retorna None (sem restrição de tenant).
    """
    if user.role == AdminRole.SUPERADMIN:
        return None
    return user.tenant_id
