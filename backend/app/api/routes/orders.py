"""Rotas de pedidos (CRUD + atualização de status)."""

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.middleware.auth import get_current_admin
from app.database.session import get_db
from app.models.admin_user import AdminUser
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate

router = APIRouter()


@router.get("/", response_model=list[OrderResponse])
async def list_orders(
    status_filter: OrderStatus | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> list[Order]:
    query = select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())

    if status_filter:
        query = query.where(Order.status == status_filter)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> Order:
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado.")

    return order


@router.patch("/{order_id}/status")
async def update_status(order_id: UUID, new_status: str, db: AsyncSession = Depends(get_db)):
    order = await db.get(Order, order_id)
    old_status = order.status
    order.status = new_status
    await db.commit()
    
    # Notifica cliente baseado na transição
    customer = await db.get(Customer, order.customer_id)
    msg = build_status_message(old_status, new_status, order)
    if msg:
        await whatsapp.send_text(customer.phone, msg)

    # Recarrega com eager load dos itens
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    return result.scalar_one()
