"""Models de produto e categoria — multi-tenant."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, UUIDType

if TYPE_CHECKING:
    from app.models.order import OrderItem
    from app.models.tenant import Tenant


class ProductCategory(UUIDMixin, TimestampMixin, Base):
    """Categoria de produtos (ex: Bebidas, Lanches)."""

    __tablename__ = "product_categories"

    tenant_id: Mapped[str] = mapped_column(
        UUIDType(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    products: Mapped[list["Product"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ProductCategory name={self.name} tenant={self.tenant_id}>"


class Product(UUIDMixin, TimestampMixin, Base):
    """Produto disponível no catálogo do tenant."""

    __tablename__ = "products"

    tenant_id: Mapped[str] = mapped_column(
        UUIDType(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    category_id: Mapped[str] = mapped_column(
        UUIDType(), ForeignKey("product_categories.id"), nullable=False
    )
    stock_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Campos de integração de estoque
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    external_source: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # bling / tiny / csv / webhook
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    category: Mapped[ProductCategory] = relationship(back_populates="products")
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="product")

    @property
    def in_stock(self) -> bool:
        """Retorna True se produto está disponível e com estoque."""
        if not self.is_available:
            return False
        if self.stock_quantity is not None and self.stock_quantity <= 0:
            return False
        return True

    def __repr__(self) -> str:
        return f"<Product name={self.name} tenant={self.tenant_id}>"
