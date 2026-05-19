"""Model do usuário administrador do dashboard — multi-tenant."""

import enum

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class AdminRole(str, enum.Enum):
    """Papel do usuário no sistema."""

    SUPERADMIN = "superadmin"       # Acesso total à plataforma
    TENANT_ADMIN = "tenant_admin"   # Admin do próprio tenant
    TENANT_VIEWER = "tenant_viewer" # Visualização somente leitura


class AdminUser(UUIDMixin, TimestampMixin, Base):
    """Usuário com acesso ao dashboard admin."""

    __tablename__ = "admin_users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Papel no sistema
    role: Mapped[AdminRole] = mapped_column(
        Enum(AdminRole),
        default=AdminRole.TENANT_ADMIN,
        nullable=False,
    )

    # NULL = superadmin (sem tenant vinculado)
    tenant_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Compat legado
    @property
    def is_superuser(self) -> bool:
        return self.role == AdminRole.SUPERADMIN

    def __repr__(self) -> str:
        return f"<AdminUser email={self.email} role={self.role}>"
