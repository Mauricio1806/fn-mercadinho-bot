"""Models de pedido e itens do pedido — multi-tenant."""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.product import Product
    from app.models.tenant import Tenant


class OrderStatus(str, enum.Enum):
    """Status possíveis de um pedido."""

    PENDING = "pending"                        # Aguardando comprovante PIX
    PAYMENT_CONFIRMED = "payment_confirmed"    # Comprovante validado — venda efetivada
    PREPARING = "preparing"                    # Em preparo pelo funcionário
    READY = "ready"                            # Pronto para entrega / retirada
    DELIVERING = "delivering"                  # Em rota de entrega
    DELIVERED = "delivered"                    # Entregue
    CANCELLED = "cancelled"                    # Cancelado


class Order(UUIDMixin, TimestampMixin, Base):
    """Pedido realizado por um cliente."""

    __tablename__ = "orders"

    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True
    )
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    delivery_building_block: Mapped[str | None] = mapped_column(String(10), nullable=True)
    delivery_apartment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    delivery_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    pix_notified: Mapped[bool] = mapped_column(default=False, nullable=False)
    owner_notified: Mapped[bool] = mapped_column(default=False, nullable=False)
    pix_confirmed: Mapped[bool] = mapped_column(default=False, nullable=False)
    commission_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    customer: Mapped["Customer"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} status={self.status} tenant={self.tenant_id}>"


class OrderItem(UUIDMixin, Base):
    """Item individual de um pedido."""

    __tablename__ = "order_items"

    order_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    product_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="order_items")

    @property
    def subtotal(self) -> float:
        """Subtotal deste item (quantidade × preço unitário)."""
        return float(self.quantity) * float(self.unit_price)

    def __repr__(self) -> str:
        return f"<OrderItem product={self.product_name} qty={self.quantity}>"
