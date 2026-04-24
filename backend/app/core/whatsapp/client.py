"""Cliente WhatsApp — envia mensagens via Evolution API."""

from __future__ import annotations

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class WhatsAppClient:
    """Envia mensagens de texto via Evolution API."""

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        instance: str | None = None,
    ) -> None:
        self._api_url = (api_url or settings.evolution_api_url).rstrip("/")
        self._api_key = api_key or settings.evolution_api_key
        self._instance = instance or settings.whatsapp_instance

    async def send_text(self, to: str, text: str) -> bool:
        """
        Envia mensagem de texto para um número.
        `to` deve estar no formato E.164 sem + (ex: '5571999990001').
        Retorna True se enviado com sucesso.
        """
        url = f"{self._api_url}/message/sendText/{self._instance}"
        payload = {
            "number": to,
            "text": text,
            "delay": 1000,  # ms de delay humanizado
        }
        headers = {"apikey": self._api_key, "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                logger.info("Mensagem enviada para %s", to)
                return True
        except httpx.TimeoutException:
            logger.error("Timeout ao enviar mensagem para %s", to)
            return False
        except httpx.HTTPStatusError as e:
            logger.error("Erro HTTP ao enviar para %s: %s", to, e.response.status_code)
            return False
        except Exception as e:
            logger.exception("Erro inesperado ao enviar mensagem para %s: %s", to, e)
            return False

    async def send_typing(self, to: str, duration_ms: int = 2000) -> None:
        """Simula digitação antes de enviar (humaniza a resposta)."""
        url = f"{self._api_url}/chat/sendPresence/{self._instance}"
        payload = {"number": to, "delay": duration_ms, "presence": "composing"}
        headers = {"apikey": self._api_key}

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(url, json=payload, headers=headers)
        except Exception:
            pass

    async def send_audio_url(self, to: str, audio_url: str) -> bool:
        """Envia mensagem de áudio via URL pública (Evolution API)."""
        url = f"{self._api_url}/message/sendMedia/{self._instance}"
        payload = {
            "number": to,
            "mediatype": "audio",
            "media": audio_url,
            "fileName": "alert.mp3",
        }
        headers = {"apikey": self._api_key, "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return True
        except Exception:
            logger.warning("Falhou ao enviar áudio de alerta para %s", to)
            return False

    async def send_image_url(self, to: str, image_url: str, caption: str = "") -> bool:
        """Envia imagem via URL pública."""
        url = f"{self._api_url}/message/sendMedia/{self._instance}"
        payload = {
            "number": to,
            "mediatype": "image",
            "media": image_url,
            "caption": caption,
        }
        headers = {"apikey": self._api_key, "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return True
        except Exception:
            logger.warning("Falhou ao enviar imagem para %s", to)
            return False


# Instância compartilhada (pode ser sobrescrita em testes)
_client: WhatsAppClient | None = None


def get_whatsapp_client() -> WhatsAppClient:
    global _client
    if _client is None:
        _client = WhatsAppClient()
    return _client
