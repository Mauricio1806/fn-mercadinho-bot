"""Model de registro anti-fraude Pix."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class PixReceiptLog(UUIDMixin, Base):
    """Cada comprovante validado é registrado aqui para evitar reuso."""

    __tablename__ = "pix_receipt_logs"

    receipt_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(String(36), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    pix_txid: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    recipient_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payment_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    flag_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
