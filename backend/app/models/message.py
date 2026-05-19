"""Model de mensagem individual numa conversa."""

import enum

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, UUIDType

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class MessageDirection(str, enum.Enum):
    """Direção da mensagem."""

    INBOUND = "inbound"    # Cliente → Bot
    OUTBOUND = "outbound"  # Bot → Cliente


class MessageType(str, enum.Enum):
    """Tipo de conteúdo da mensagem."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    DOCUMENT = "document"


class Message(UUIDMixin, TimestampMixin, Base):
    """Mensagem individual trocada numa conversa."""

    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(
        UUIDType(), ForeignKey("conversations.id"), nullable=False, index=True
    )
    direction: Mapped[MessageDirection] = mapped_column(
        Enum(MessageDirection), nullable=False
    )
    message_type: Mapped[MessageType] = mapped_column(
        Enum(MessageType), default=MessageType.TEXT, nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    whatsapp_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(nullable=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        preview = self.content[:40] if self.content else ""
        return f"<Message {self.direction} '{preview}'>"
