"""
TenantResolver — resolve o tenant a partir do número WhatsApp de destino.

Cache em memória com TTL para evitar queries repetidas ao banco.
Normaliza números no formato internacional (sem '+').
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.tenancy.context import TenantContext

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Cache simples em memória: {numero_normalizado: (TenantContext, timestamp)}
_cache: dict[str, tuple[TenantContext, float]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutos


def normalize_phone(phone: str) -> str:
    """
    Normaliza número de telefone para formato sem '+' e sem espaços.
    Ex: '+55 71 99999-9999' → '5571999999999'
    """
    return "".join(c for c in phone if c.isdigit())


async def resolve_tenant_by_number(
    number: str,
    db: AsyncSession,
) -> TenantContext | None:
    """
    Resolve o tenant pelo número WhatsApp do bot (campo whatsapp_number).

    Args:
        number: Número de destino da mensagem (formato qualquer)
        db: Sessão assíncrona do banco

    Returns:
        TenantContext se encontrado, None caso contrário
    """
    normalized = normalize_phone(number)

    # Verifica cache
    cached = _cache.get(normalized)
    if cached:
        ctx, ts = cached
        if time.monotonic() - ts < _CACHE_TTL_SECONDS:
            logger.debug("Tenant resolvido do cache: %s → %s", normalized, ctx.slug)
            return ctx
        else:
            del _cache[normalized]

    # Busca no banco
    result = await db.execute(
        select(Tenant).where(
            Tenant.whatsapp_number == normalized,
            Tenant.is_active == True,  # noqa: E712
        )
    )
    tenant = result.scalar_one_or_none()

    if tenant is None:
        logger.warning("Tenant não encontrado para número: %s", normalized)
        return None

    ctx = TenantContext.from_orm(tenant)

    # Popula cache
    _cache[normalized] = (ctx, time.monotonic())
    logger.info("Tenant resolvido do banco: %s → %s", normalized, ctx.slug)

    return ctx


async def resolve_tenant_by_id(
    tenant_id: str,
    db: AsyncSession,
) -> TenantContext | None:
    """Resolve o tenant pelo UUID."""
    import uuid as _uuid

    try:
        uid = _uuid.UUID(str(tenant_id))
    except (ValueError, AttributeError):
        return None

    result = await db.execute(
        select(Tenant).where(Tenant.id == uid, Tenant.is_active == True)  # noqa: E712
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        return None
    return TenantContext.from_orm(tenant)


async def resolve_tenant_by_slug(
    slug: str,
    db: AsyncSession,
) -> TenantContext | None:
    """Resolve o tenant pelo slug (usado em webhooks inbound identificados por URL)."""
    result = await db.execute(
        select(Tenant).where(Tenant.slug == slug, Tenant.is_active == True)  # noqa: E712
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        return None
    return TenantContext.from_orm(tenant)


def invalidate_cache(number: str | None = None) -> None:
    """Invalida cache para um número ou todo o cache se number=None."""
    if number is None:
        _cache.clear()
        logger.info("Cache de tenants limpo.")
    else:
        normalized = normalize_phone(number)
        _cache.pop(normalized, None)
