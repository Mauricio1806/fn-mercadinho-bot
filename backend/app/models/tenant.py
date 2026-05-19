"""Model do tenant (cliente da plataforma SaaS)."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Tenant(UUIDMixin, TimestampMixin, Base):
    """Cliente da plataforma — cada tenant é um negócio independente."""

    __tablename__ = "tenants"

    # Identificação
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Número WhatsApp do bot deste tenant (ex: "557199371599")
    whatsapp_number: Mapped[str | None] = mapped_column(
        String(30), unique=True, nullable=True, index=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Config JSONB — validado pelo TenantConfig Pydantic model
    # Inclui: pix, horario, delivery, owners, persona, branding, integracao_estoque
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<Tenant slug={self.slug} name={self.name}>"

    @property
    def config_safe(self) -> dict:
        """Retorna config ou dict vazio se None."""
        return self.config or {}
