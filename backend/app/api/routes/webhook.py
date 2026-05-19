"""Webhook da Evolution API — multi-tenant: resolve tenant pelo número de destino."""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.conversation.engine import ConversationEngine
from app.core.whatsapp.webhook_parser import parse_webhook
from app.database.session import get_db
from app.tenancy.defaults import FN_MERCADINHO_UUID
from app.tenancy.resolver import resolve_tenant_by_number

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


def verify_webhook_signature(body: bytes, signature: str | None) -> bool:
    """Valida assinatura HMAC do webhook da Evolution API."""
    if not signature:
        return not settings.is_production

    expected = hmac.new(
        settings.evolution_api_key.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


@router.post("/")
async def receive_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_hub_signature: str | None = Header(default=None, alias="x-hub-signature-256"),
) -> dict[str, str]:
    """
    Recebe webhook da Evolution API.
    1. Parseia a mensagem
    2. Resolve o tenant pelo número de destino (to_number)
    3. Instancia ConversationEngine com contexto do tenant
    4. Processa a mensagem
    """
    body = await request.body()

    if not verify_webhook_signature(body, x_hub_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assinatura do webhook inválida.",
        )

    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload inválido.",
        )

    event_type = payload.get("event", "unknown")
    logger.debug("Webhook recebido: event=%s", event_type)

    inbound = parse_webhook(payload)

    if inbound is None:
        logger.debug("Evento ignorado (não é mensagem de usuário): %s", event_type)
        return {"status": "ignored"}

    # ── Resolução de tenant ───────────────────────────────────────────────
    # O campo to_number indica qual instância do bot recebeu a mensagem
    to_number = payload.get("instance", "") or getattr(inbound, "instance", "")

    tenant_ctx = None
    if to_number:
        tenant_ctx = await resolve_tenant_by_number(to_number, db)

    # Fallback: usa FN Mercadinho se tenant não identificado
    if tenant_ctx is None:
        logger.warning(
            "Tenant não encontrado para número '%s' — usando fallback FN Mercadinho", to_number
        )
        from app.tenancy.resolver import resolve_tenant_by_id
        tenant_ctx = await resolve_tenant_by_id(FN_MERCADINHO_UUID, db)

    if tenant_ctx is None:
        logger.error("Fallback tenant também não encontrado! Ignorando mensagem.")
        return {"status": "tenant_not_found"}

    # ── Processa com o engine do tenant ──────────────────────────────────
    try:
        engine = ConversationEngine(db=db, business=tenant_ctx)
        await engine.handle(inbound)
    except Exception:
        logger.exception(
            "Erro ao processar mensagem de %s (tenant=%s)", inbound.phone, tenant_ctx.slug
        )

    return {"status": "processed"}
