"""Model do cliente (quem envia mensagens no WhatsApp)."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.order import Order


class Customer(UUIDMixin, TimestampMixin, Base):
    """Cliente identificado pelo número do WhatsApp."""

    __tablename__ = "customers"

    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    building_block: Mapped[str | None] = mapped_column(String(10), nullable=True)
    apartment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    total_orders: Mapped[int] = mapped_column(default=0, nullable=False)

    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    orders: Mapped[list["Order"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Customer phone={self.phone} name={self.name}>"
