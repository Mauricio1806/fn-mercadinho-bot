from __future__ import annotations
import httpx
import logging

logger = logging.getLogger(__name__)

BRIDGE_URL = "http://172.18.0.1:3001/send"


async def send_text_message(phone: str, text: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(BRIDGE_URL, json={"phone": phone, "text": text})
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Erro ao enviar para {phone}: {e}")
        return False


async def send_image_message(phone: str, image_url: str, caption: str = "") -> bool:
    return await send_text_message(phone, caption or image_url)


class WhatsAppClient:
    async def send_text(self, phone: str, text: str) -> bool:
        return await send_text_message(phone, text)

    async def send_image(self, phone: str, image_url: str, caption: str = "") -> bool:
        return await send_image_message(phone, image_url, caption)

    async def send_message(self, phone: str, text: str) -> bool:
        return await send_text_message(phone, text)

    async def send_typing(self, phone: str, duration_ms: int = 1500) -> bool:
        return True

    async def send_audio(self, phone: str, audio_url: str) -> bool:
        return True

    async def send_reaction(self, phone: str, message_id: str, emoji: str) -> bool:
        return True


def get_whatsapp_client() -> WhatsAppClient:
    return WhatsAppClient()
