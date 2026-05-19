"""Model do tenant (cliente da plataforma SaaS)."""

from __future__ import annotations

from sqlalchemy import Boolean, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin, UUIDType


class Tenant(UUIDMixin, TimestampMixin, Base):
    """Cliente da plataforma — cada tenant é um negócio independente."""

    __tablename__ = "tenants"

    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    whatsapp_number: Mapped[str | None] = mapped_column(
        String(30), unique=True, nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # JSON agnóstico: JSONB no PostgreSQL, TEXT no SQLite (testes)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<Tenant slug={self.slug} name={self.name}>"

    @property
    def config_safe(self) -> dict:
        return self.config or {}
