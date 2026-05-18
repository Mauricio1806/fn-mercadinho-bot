"""Model de conversa (sessão de atendimento)."""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.message import Message


class ConversationStatus(str, enum.Enum):
    """Status da conversa de atendimento."""

    ACTIVE = "active"            # Conversa em andamento
    WAITING = "waiting"          # Aguardando resposta do cliente
    HUMAN_TAKEOVER = "human"     # Atendente humano assumiu
    CLOSED = "closed"            # Encerrada


class ConversationState(str, enum.Enum):
    """Estado atual na máquina de estados da conversa."""

    GREETING = "greeting"
    MAIN_MENU = "main_menu"
    ORDER_ITEMS = "order_items"
    ORDER_CONFIRM = "order_confirm"
    ORDER_DELIVERY = "order_delivery"
    ORDER_PAYMENT = "order_payment"
    PAYMENT_RECEIPT = "payment_receipt"  # Aguardando comprovante PIX do cliente
    DELIVERY_INFO = "delivery_info"
    HOURS_INFO = "hours_info"
    FREE_CHAT = "free_chat"
    CLOSED = "closed"


class Conversation(UUIDMixin, TimestampMixin, Base):
    """Sessão de conversa entre o bot e um cliente."""

    __tablename__ = "conversations"

    customer_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50),
        default=ConversationStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    state: Mapped[str] = mapped_column(
        String(50),
        default=ConversationState.GREETING,
        nullable=False,
    )
    context_json: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    customer: Mapped["Customer"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} state={self.state} status={self.status}>"
