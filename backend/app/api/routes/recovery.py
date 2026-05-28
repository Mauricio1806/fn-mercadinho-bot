"""
Endpoints para gerenciar recuperação de carrinho por tenant.
Superadmin ativa/desativa para cada cliente individualmente.
"""
from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.tenant import Tenant
from app.api.middleware.tenant_scope import get_current_role
from app.core.recovery.scheduler import (
    activate_recovery_for_tenant,
    deactivate_recovery_for_tenant,
    list_active_recovery_tenants,
)
from sqlalchemy import select

router = APIRouter()


def require_superadmin(role: str = Depends(get_current_role)) -> str:
    if role != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas superadmin.")
    return role


class RecoveryConfig(BaseModel):
    minutes_threshold: int = 15
    message_1: str = (
        "Oi! 👋 Vi que você estava montando um pedido aqui.\n\n"
        "Ainda quer finalizar? É só me dizer que eu retomo de onde paramos! 🛒"
    )
    message_2: str = (
        "Passando pra lembrar que estamos abertos e com tudo fresquinho! 😊\n\n"
        "Que tal aproveitar e fazer seu pedido hoje? 🛍️"
    )


@router.post("/{tenant_id}/activate", status_code=status.HTTP_200_OK)
async def activate_recovery(
    tenant_id: UUID,
    config: RecoveryConfig,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_superadmin),
) -> dict:
    """
    Ativa recuperação de carrinho para um tenant.
    Salva config no JSONB do tenant e inicia o job scheduler.
    """
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado.")

    # Salva config no JSONB do tenant
    tenant_config = tenant.config or {}
    tenant_config["recovery"] = {
        "enabled": True,
        "minutes_threshold": config.minutes_threshold,
        "message_1": config.message_1,
        "message_2": config.message_2,
    }
    tenant.config = tenant_config
    await db.commit()

    # Ativa scheduler
    activated = activate_recovery_for_tenant(tenant_id, tenant_config)

    return {
        "status": "activated" if activated else "already_active",
        "tenant_id": str(tenant_id),
        "config": tenant_config["recovery"],
    }


@router.post("/{tenant_id}/deactivate", status_code=status.HTTP_200_OK)
async def deactivate_recovery(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_superadmin),
) -> dict:
    """Desativa recuperação de carrinho para um tenant."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado.")

    # Remove config do JSONB
    tenant_config = tenant.config or {}
    if "recovery" in tenant_config:
        tenant_config["recovery"]["enabled"] = False
        tenant.config = tenant_config
        await db.commit()

    deactivated = deactivate_recovery_for_tenant(tenant_id)

    return {
        "status": "deactivated" if deactivated else "was_not_active",
        "tenant_id": str(tenant_id),
    }


@router.get("/active", status_code=status.HTTP_200_OK)
async def list_active(
    _: str = Depends(require_superadmin),
) -> dict:
    """Lista tenants com recovery ativo no momento."""
    return {"active_tenants": list_active_recovery_tenants()}


@router.get("/{tenant_id}/status", status_code=status.HTTP_200_OK)
async def recovery_status(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_superadmin),
) -> dict:
    """Retorna status e config atual da recuperação para um tenant."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado.")

    recovery_cfg = (tenant.config or {}).get("recovery", {})
    active_jobs = list_active_recovery_tenants()

    return {
        "tenant_id": str(tenant_id),
        "enabled_in_config": recovery_cfg.get("enabled", False),
        "scheduler_running": str(tenant_id) in active_jobs,
        "config": recovery_cfg,
    }
