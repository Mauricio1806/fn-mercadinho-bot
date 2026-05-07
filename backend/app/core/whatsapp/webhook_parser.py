from __future__ import annotations
import logging
from typing import Optional
from app.core.whatsapp.types import InboundMessage, WhatsAppMessageType

logger = logging.getLogger(__name__)


def parse_whatsapp_message(data: dict) -> Optional[InboundMessage]:
    try:
        if data.get("event") != "messages.upsert":
            return None
        msg_data = data.get("data", {})
        if msg_data.get("key", {}).get("fromMe", False):
            return None

        parsed = msg_data.get("_parsed", {})
        phone = parsed.get("phone", "")
        text = parsed.get("text", "").strip()
        has_image = parsed.get("hasImage", False)
        push_name = msg_data.get("pushName", "")
        msg_id = msg_data.get("key", {}).get("id", "")
        timestamp = int(msg_data.get("messageTimestamp", 0))

        if not phone:
            return None

        if has_image:
            msg_type = WhatsAppMessageType.IMAGE
        elif text:
            msg_type = WhatsAppMessageType.TEXT
        else:
            return None

        if not text and not has_image:
            return None

        # Montar data URI se vier base64 da mídia
        image_url = None
        media_b64 = parsed.get("mediaBase64")
        media_mime = parsed.get("mediaMimetype", "image/jpeg")
        if media_b64 and has_image:
            image_url = f"data:{media_mime};base64,{media_b64}"

        return InboundMessage(
            phone=phone,
            name=push_name or None,
            text=text,
            message_id=msg_id,
            message_type=msg_type,
            timestamp=timestamp,
            image_url=image_url,
        )
    except Exception as e:
        logger.error(f"Erro ao parsear webhook: {e}", exc_info=True)
        return None
