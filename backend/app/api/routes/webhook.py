"""Webhook da Evolution API — recebe e processa mensagens do WhatsApp."""

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

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


def verify_webhook_signature(body: bytes, signature: str | None) -> bool:
    """Valida assinatura HMAC do webhook da Evolution API."""
    if not signature:
        # Em desenvolvimento, permite sem assinatura
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
    Parseia a mensagem e despacha para o ConversationEngine.
    Retorna 200 imediatamente — processamento é fire-and-forget (sem await bloqueante).
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

    # Parseia payload para InboundMessage
    inbound = parse_webhook(payload)

    if inbound is None:
        logger.debug("Evento ignorado (não é mensagem de usuário): %s", event_type)
        return {"status": "ignored"}

    # Processa a mensagem
    try:
        engine = ConversationEngine(db=db)
        await engine.handle(inbound)
    except Exception:
        logger.exception(
            "Erro ao processar mensagem de %s", inbound.phone
        )
        # Retorna 200 mesmo com erro — não queremos que a Evolution API faça retry spam

    return {"status": "processed"}
