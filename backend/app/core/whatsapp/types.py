"""Tipos de dados para mensagens do WhatsApp / Evolution API."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, field_validator


class WhatsAppMessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    DOCUMENT = "document"
    STICKER = "sticker"
    LOCATION = "location"
    REACTION = "reaction"
    UNKNOWN = "unknown"


class InboundMessage(BaseModel):
    """Mensagem recebida do WhatsApp, já parseada do payload da Evolution API."""

    phone: str             # Número do remetente, formato E.164 sem +: "5571999990001"
    name: str | None       # Nome do contato (se disponível)
    text: str              # Conteúdo textual (vazio para mídia)
    message_id: str        # ID da mensagem no WhatsApp
    message_type: WhatsAppMessageType
    timestamp: int         # Unix timestamp
    image_url: str | None = None   # URL da imagem (se message_type == IMAGE)

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        """Remove @s.whatsapp.net e garante apenas dígitos + código de país."""
        v = str(v).split("@")[0].strip()
        # Remove caracteres não numéricos exceto +
        digits = "".join(c for c in v if c.isdigit())
        return digits

    @property
    def e164(self) -> str:
        """Retorna número no formato E.164 com + (ex: +5571999990001)."""
        return f"+{self.phone}"

    def is_text(self) -> bool:
        return self.message_type == WhatsAppMessageType.TEXT

    def __repr__(self) -> str:
        return f"<InboundMessage from={self.phone} text='{self.text[:40]}'>"


class OutboundMessage(BaseModel):
    """Mensagem a ser enviada via WhatsApp."""

    to: str        # Número do destinatário (E.164 sem +)
    text: str      # Texto a enviar

    @field_validator("to", mode="before")
    @classmethod
    def normalize_to(cls, v: str) -> str:
        return str(v).lstrip("+").replace(" ", "")
