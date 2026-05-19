"""Rotas de tenants — CRUD restrito a superadmin."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_superadmin
from app.database.session import get_db
from app.models.admin_user import AdminUser
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantOut, TenantSummary, TenantUpdate
from app.tenancy.resolver import invalidate_cache

router = APIRouter()


@router.get("/", response_model=list[TenantSummary])
async def list_tenants(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_superadmin),
) -> list[Tenant]:
    """Lista todos os tenants (apenas superadmin)."""
    query = select(Tenant).order_by(Tenant.created_at.asc())
    if not include_inactive:
        query = query.where(Tenant.is_active == True)  # noqa: E712
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantCreate,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_superadmin),
) -> Tenant:
    """Cria novo tenant (apenas superadmin)."""
    # Verifica slug único
    existing = await db.execute(select(Tenant).where(Tenant.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slug '{body.slug}' já está em uso.",
        )

    tenant = Tenant(
        slug=body.slug,
        name=body.name,
        whatsapp_number=body.whatsapp_number,
        config=body.config,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.get("/{tenant_id}", response_model=TenantOut)
async def get_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_superadmin),
) -> Tenant:
    """Retorna detalhes de um tenant (apenas superadmin)."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado.")
    return tenant


@router.patch("/{tenant_id}", response_model=TenantOut)
async def update_tenant(
    tenant_id: uuid.UUID,
    body: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_superadmin),
) -> Tenant:
    """
    Atualiza tenant com merge parcial do config JSONB.
    O campo config é mesclado (não substituído completamente).
    Apenas superadmin.
    """
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado.")

    if body.name is not None:
        tenant.name = body.name
    if body.whatsapp_number is not None:
        tenant.whatsapp_number = body.whatsapp_number
    if body.is_active is not None:
        tenant.is_active = body.is_active

    # Merge parcial do config JSONB
    if body.config is not None:
        existing_config = tenant.config or {}
        merged = {**existing_config, **body.config}
        tenant.config = merged

    await db.commit()
    await db.refresh(tenant)

    # Invalida cache do resolver para este número
    if tenant.whatsapp_number:
        invalidate_cache(tenant.whatsapp_number)

    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_superadmin),
) -> None:
    """
    Desativa tenant (soft delete — is_active = False).
    Dados são preservados. Apenas superadmin.
    """
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado.")

    tenant.is_active = False
    await db.commit()

    if tenant.whatsapp_number:
        invalidate_cache(tenant.whatsapp_number)
