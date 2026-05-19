"""
Tenant scope middleware — extrai tenant_id do JWT e injeta como contexto.

Usado como Dependency nas rotas para garantir isolamento automático.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_admin, get_tenant_id_from_user
from app.database.session import get_db
from app.models.admin_user import AdminRole, AdminUser


class TenantScope:
    """Encapsula o contexto de acesso de um usuário autenticado."""

    def __init__(self, user: AdminUser, tenant_id: _uuid.UUID | None) -> None:
        self.user = user
        self.tenant_id = tenant_id  # None = superadmin sem restrição
        self.is_superadmin = user.role == AdminRole.SUPERADMIN

    def apply_filter(self, query, model_cls):
        """
        Aplica filtro de tenant_id em uma query SQLAlchemy se necessário.

        Superadmin: sem filtro (vê tudo).
        Tenant admin: filtra pelo tenant_id.
        """
        if self.is_superadmin or self.tenant_id is None:
            return query
        return query.where(model_cls.tenant_id == self.tenant_id)

    def assert_owns_tenant(self, tenant_id: _uuid.UUID | str) -> None:
        """
        Garante que o usuário pode acessar o tenant_id especificado.
        Superadmin pode acessar qualquer tenant.
        """
        if self.is_superadmin:
            return
        try:
            requested = _uuid.UUID(str(tenant_id))
        except (ValueError, AttributeError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tenant_id inválido.")
        if self.tenant_id != requested:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: você não tem permissão para este tenant.",
            )

    def effective_tenant_id(self, requested: _uuid.UUID | None = None) -> _uuid.UUID | None:
        """
        Retorna o tenant_id efetivo para uma operação.
        Superadmin: usa o tenant_id solicitado (ou None para ver tudo).
        Tenant admin: sempre usa o próprio tenant_id.
        """
        if self.is_superadmin:
            return requested
        return self.tenant_id


async def get_tenant_scope(
    user: AdminUser = Depends(get_current_admin),
) -> TenantScope:
    """Dependency que retorna o TenantScope do usuário atual."""
    tenant_id = get_tenant_id_from_user(user)
    return TenantScope(user=user, tenant_id=tenant_id)
