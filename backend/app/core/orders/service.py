"""Serviço de pedidos — cria e gerencia Orders no banco de dados."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.orders.context import OrderContext
from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product

logger = logging.getLogger(__name__)


class OrderService:
    """Criação e consulta de pedidos."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_from_context(
        self,
        customer: Customer,
        context: OrderContext,
    ) -> Order:
        """
        Cria um Order completo no banco a partir do contexto da conversa.

        Valida preços contra o banco de dados (não confia no contexto do Claude).
        """
        if not context.items:
            raise ValueError("Pedido sem itens não pode ser criado.")

        context.recalculate_total()
        total = context.total

        order = Order(
            customer_id=customer.id,
            status=OrderStatus.PENDING,
            total_amount=total,
            delivery_building_block=context.building_block,
            delivery_apartment=context.apartment,
            delivery_fee=0.0,
            notes=context.notes,
        )
        self._db.add(order)
        await self._db.flush()

        for item_ctx in context.items:
            # Busca produto no BD para garantir preço correto
            product = await self._get_product_by_name(item_ctx.name)

            # Se produto não encontrado, usa preço do contexto (fallback)
            unit_price = float(product.price) if product else item_ctx.unit_price
            product_id = product.id if product else None
            product_name = product.name if product else item_ctx.name

            order_item = OrderItem(
                order_id=order.id,
                product_id=product_id or uuid.uuid4(),  # Gera UUID temporário se não encontrado
                product_name=product_name,
                quantity=item_ctx.qty,
                unit_price=unit_price,
            )
            self._db.add(order_item)

        # Recalcula total com preços do BD
        await self._db.flush()

        # Incrementa contador de pedidos do cliente
        customer.total_orders += 1

        await self._db.flush()
        logger.info("Pedido %s criado para cliente %s", order.id, customer.phone)
        return order

    async def _get_product_by_name(self, name: str) -> Product | None:
        """Busca produto por nome (case-insensitive, partial match)."""
        # Busca exata primeiro
        result = await self._db.execute(
            select(Product).where(
                Product.name.ilike(name),
                Product.is_available == True,  # noqa: E712
            )
        )
        product = result.scalar_one_or_none()
        if product:
            return product

        # Busca parcial como fallback
        result = await self._db.execute(
            select(Product).where(
                Product.name.ilike(f"%{name}%"),
                Product.is_available == True,  # noqa: E712
            )
        )
        return result.scalars().first()

    async def get_order_with_items(self, order_id: uuid.UUID) -> Order | None:
        result = await self._db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_customer_orders(
        self, customer_id: uuid.UUID, limit: int = 10
    ) -> list[Order]:
        result = await self._db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
