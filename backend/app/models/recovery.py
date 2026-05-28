"""Model para rastreamento de tentativas de recuperação de carrinho."""
from __future__ import annotations
import enum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDMixin


class RecoveryStatus(str, enum.Enum):
    PENDING   = "pending"    # agendado, ainda não enviado
    SENT      = "sent"       # primeira mensagem enviada
    REMINDED  = "reminded"   # lembrete do dia seguinte enviado
    CONVERTED = "converted"  # cliente voltou e comprou
    EXPIRED   = "expired"    # nenhuma resposta — encerrado


class RecoveryAttempt(UUIDMixin, TimestampMixin, Base):
    """Registra cada tentativa de recuperação de carrinho por conversa."""
    __tablename__ = "recovery_attempts"

    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True
    )
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=RecoveryStatus.PENDING, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    cart_summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON dos itens
