"""Model do usuário administrador do dashboard — multi-tenant."""

import enum

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, UUIDType


class AdminRole(str, enum.Enum):
    SUPERADMIN = "superadmin"
    TENANT_ADMIN = "tenant_admin"
    TENANT_VIEWER = "tenant_viewer"


class AdminUser(UUIDMixin, TimestampMixin, Base):
    """Usuário com acesso ao dashboard admin."""

    __tablename__ = "admin_users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # must_change_password e password_changed_at — temporariamente removidos
    # readicionar depois de rodar migration 006 manualmente no Railway

    role: Mapped[AdminRole] = mapped_column(
        Enum(AdminRole),
        default=AdminRole.TENANT_ADMIN,
        nullable=False,
    )

    # NULL = superadmin (sem tenant vinculado)
    tenant_id: Mapped[str | None] = mapped_column(
        UUIDType(),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    @property
    def is_superuser(self) -> bool:
        return self.role == AdminRole.SUPERADMIN

    def __repr__(self) -> str:
        return f"<AdminUser email={self.email} role={self.role}>"
