"""Rotas de gerenciamento de tenants — acesso restrito a superadmin."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.tenant import Tenant
from app.api.middleware.tenant_scope import get_current_role

router = APIRouter()


def require_superadmin(role: str = Depends(get_current_role)) -> str:
    if role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a superadmin.",
        )
    return role


# ── Schemas ───────────────────────────────────────────────────────────────────

class TenantCreate(BaseModel):
    slug: str
    name: str
    whatsapp_number: str
    config: dict = {}
    ai_model: str = "claude-haiku-4-5-20251001"


class TenantUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None
    ai_model: str | None = None
    active: bool | None = None


class TenantOut(BaseModel):
    id: str
    slug: str
    name: str
    whatsapp_number: str
    ai_model: str
    active: bool
    config: dict

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[TenantOut])
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_superadmin),
) -> list[TenantOut]:
    result = await db.execute(select(Tenant).order_by(Tenant.name))
    tenants = result.scalars().all()
    return [TenantOut(
        id=str(t.id), slug=t.slug, name=t.name,
        whatsapp_number=t.whatsapp_number, ai_model=t.ai_model,
        active=t.active, config=t.config or {},
    ) for t in tenants]


@router.post("/", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_superadmin),
) -> TenantOut:
    existing = await db.execute(
        select(Tenant).where(
            (Tenant.slug == body.slug) | (Tenant.whatsapp_number == body.whatsapp_number)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slug ou número WhatsApp já cadastrado.",
        )
    tenant = Tenant(
        id=uuid.uuid4(),
        slug=body.slug,
        name=body.name,
        whatsapp_number=body.whatsapp_number,
        config=body.config,
        ai_model=body.ai_model,
        active=True,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return TenantOut(
        id=str(tenant.id), slug=tenant.slug, name=tenant.name,
        whatsapp_number=tenant.whatsapp_number, ai_model=tenant.ai_model,
        active=tenant.active, config=tenant.config or {},
    )


@router.get("/{tenant_id}", response_model=TenantOut)
async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_superadmin),
) -> TenantOut:
    result = await db.execute(select(Tenant).where(Tenant.id == uuid.UUID(tenant_id)))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado.")
    return TenantOut(
        id=str(tenant.id), slug=tenant.slug, name=tenant.name,
        whatsapp_number=tenant.whatsapp_number, ai_model=tenant.ai_model,
        active=tenant.active, config=tenant.config or {},
    )


@router.patch("/{tenant_id}", response_model=TenantOut)
async def update_tenant(
    tenant_id: str,
    body: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_superadmin),
) -> TenantOut:
    result = await db.execute(select(Tenant).where(Tenant.id == uuid.UUID(tenant_id)))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado.")
    if body.name is not None:
        tenant.name = body.name
    if body.config is not None:
        tenant.config = {**(tenant.config or {}), **body.config}
    if body.ai_model is not None:
        tenant.ai_model = body.ai_model
    if body.active is not None:
        tenant.active = body.active
    await db.commit()
    await db.refresh(tenant)
    return TenantOut(
        id=str(tenant.id), slug=tenant.slug, name=tenant.name,
        whatsapp_number=tenant.whatsapp_number, ai_model=tenant.ai_model,
        active=tenant.active, config=tenant.config or {},
    )


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_superadmin),
) -> None:
    """Desativa tenant — não apaga dados."""
    result = await db.execute(select(Tenant).where(Tenant.id == uuid.UUID(tenant_id)))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado.")
    tenant.active = False
    await db.commit()
