"""Model para vendas recuperáveis — base do cart recovery multi-tenant."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, JSON, Numeric, String, UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin, UUIDType


class RecoverySaleStatus(str, enum.Enum):
    PENDING = "pending"
    CONTACTED = "contacted"
    RECOVERED = "recovered"
    EXPIRED = "expired"
    LOST = "lost"


class RecoveryFunnelStage(str, enum.Enum):
    PIX_PENDENTE = "pix_pendente"
    ABANDONO = "abandono"


class RecoverableSale(UUIDMixin, TimestampMixin, Base):
    """Venda pendente ou abandonada capturada de um checkout externo (ex: Payt)."""

    __tablename__ = "recoverable_sales"

    __table_args__ = (
        UniqueConstraint("tenant_id", "external_id", name="uq_recoverable_sale_tenant_external"),
    )

    tenant_id: Mapped[str] = mapped_column(
        UUIDType(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    customer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    customer_phone: Mapped[str] = mapped_column(String(30), nullable=False)

    product_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    checkout_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    pix_code: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    coupon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attribution: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    status: Mapped[RecoverySaleStatus] = mapped_column(
        Enum(RecoverySaleStatus),
        default=RecoverySaleStatus.PENDING,
        nullable=False,
        index=True,
    )
    funnel_stage: Mapped[RecoveryFunnelStage] = mapped_column(
        Enum(RecoveryFunnelStage),
        nullable=False,
    )
    abandoned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<RecoverableSale tenant={self.tenant_id} "
            f"stage={self.funnel_stage} status={self.status}>"
        )
