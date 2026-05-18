"""Resolve qual tenant corresponde a um número WhatsApp."""
from __future__ import annotations
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.tenancy.context import TenantContext

logger = logging.getLogger(__name__)


async def resolve_tenant_by_number(
    whatsapp_number: str,
    db: AsyncSession,
) -> TenantContext | None:
    """
    Busca o tenant pelo número WhatsApp que recebeu a mensagem.
    Retorna TenantContext pronto ou None se não encontrado/inativo.
    """
    # Normaliza número — remove + se tiver
    number = whatsapp_number.lstrip("+")

    result = await db.execute(
        select(Tenant).where(
            Tenant.whatsapp_number == number,
            Tenant.active == True,
        )
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        logger.warning("Nenhum tenant ativo para número: %s", number)
        return None

    return TenantContext.from_orm(tenant)
