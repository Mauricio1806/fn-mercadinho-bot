"""Parser do payload de webhook da Evolution API."""

from __future__ import annotations

import logging
from typing import Any

from app.core.whatsapp.types import InboundMessage, WhatsAppMessageType

logger = logging.getLogger(__name__)

# Eventos que contêm mensagens de usuário
MESSAGE_EVENTS = {"messages.upsert", "message.received"}


def parse_webhook(payload: dict[str, Any]) -> InboundMessage | None:
    """
    Converte o payload bruto da Evolution API em InboundMessage.
    Retorna None para eventos que não são mensagens de usuário
    (status updates, reactions de sistema, mensagens do próprio bot, etc.).
    """
    event = payload.get("event", "")

    if event not in MESSAGE_EVENTS:
        logger.debug("Evento ignorado: %s", event)
        return None

    data = payload.get("data", {})

    # Evolution API v2 structure
    key = data.get("key", {})
    msg = data.get("message", {})

    # Ignorar mensagens enviadas pelo próprio bot
    if key.get("fromMe", False):
        return None

    # Extrair remetente
    remote_jid = key.get("remoteJid", "")
    if not remote_jid or "g.us" in remote_jid:
        # Ignorar grupos
        return None

    # Extrair nome do contato
    push_name = data.get("pushName") or data.get("verifiedBizName")

    # Detectar tipo e conteúdo da mensagem
    msg_type, text = _extract_message_content(msg)

    if not text and msg_type == WhatsAppMessageType.TEXT:
        logger.debug("Mensagem sem conteúdo de texto ignorada")
        return None

    message_id = key.get("id", "unknown")
    timestamp = data.get("messageTimestamp", 0)

    return InboundMessage(
        phone=remote_jid,
        name=push_name,
        text=text,
        message_id=message_id,
        message_type=msg_type,
        timestamp=int(timestamp),
    )


def _extract_message_content(msg: dict[str, Any]) -> tuple[WhatsAppMessageType, str]:
    """Extrai tipo e texto de uma mensagem da Evolution API."""

    # Texto simples
    if "conversation" in msg:
        return WhatsAppMessageType.TEXT, str(msg["conversation"]).strip()

    # Texto estendido (com preview de link, etc)
    if "extendedTextMessage" in msg:
        text = msg["extendedTextMessage"].get("text", "")
        return WhatsAppMessageType.TEXT, str(text).strip()

    # Imagem com legenda
    if "imageMessage" in msg:
        caption = msg["imageMessage"].get("caption", "")
        return WhatsAppMessageType.IMAGE, str(caption).strip()

    # Áudio
    if "audioMessage" in msg:
        return WhatsAppMessageType.AUDIO, ""

    # Documento
    if "documentMessage" in msg:
        return WhatsAppMessageType.DOCUMENT, ""

    # Sticker
    if "stickerMessage" in msg:
        return WhatsAppMessageType.STICKER, ""

    # Reaction
    if "reactionMessage" in msg:
        return WhatsAppMessageType.REACTION, ""

    return WhatsAppMessageType.UNKNOWN, ""
