"""Protocols e ABCs do sistema multi-tenant."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.tenancy.context import TenantContext


@runtime_checkable
class TenantAware(Protocol):
    """Protocol para objetos que carregam contexto de tenant."""

    @property
    def tenant_id(self) -> str:
        """UUID do tenant como string."""
        ...


@runtime_checkable
class TenantConfigReader(Protocol):
    """Protocol para leitores de config de tenant."""

    def get_tenant_context(self, tenant_id: str) -> TenantContext | None:
        ...
