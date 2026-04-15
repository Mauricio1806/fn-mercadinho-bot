"""Webhook da Evolution API — recebe mensagens do WhatsApp."""

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


def verify_webhook_signature(body: bytes, signature: str | None) -> bool:
    """Valida a assinatura HMAC do webhook da Evolution API."""
    if not signature:
        return settings.env != "production"

    expected = hmac.new(
        settings.evolution_api_key.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


@router.post("/")
async def receive_webhook(
    request: Request,
    x_hub_signature: str | None = Header(default=None, alias="x-hub-signature-256"),
) -> dict[str, str]:
    """
    Recebe webhook da Evolution API com mensagens do WhatsApp.
    O processamento real da conversa será implementado no Dia 2.
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
    logger.info("Webhook recebido: event=%s", event_type)

    # TODO Dia 2: processar mensagem e disparar conversation engine
    # from app.core.conversation.engine import ConversationEngine
    # await ConversationEngine.handle_webhook(payload)

    return {"status": "received"}
