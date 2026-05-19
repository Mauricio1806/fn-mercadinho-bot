"""Rotas de pedidos — multi-tenant com notificação de status ao cliente."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.middleware.auth import get_current_admin
from app.api.middleware.tenant_scope import TenantScope, get_tenant_scope
from app.database.session import get_db
from app.models.admin_user import AdminUser
from app.models.order import Order, OrderStatus
from app.platform.notifications.customer_updates import send_status_notification
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate

router = APIRouter()


@router.get("/", response_model=list[OrderResponse])
async def list_orders(
    status_filter: OrderStatus | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    scope: TenantScope = Depends(get_tenant_scope),
) -> list[Order]:
    """Lista pedidos filtrados por tenant."""
    query = (
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
    )

    # Isolamento: filtra pelo tenant_id do usuário logado
    query = scope.apply_filter(query, Order)

    if status_filter:
        query = query.where(Order.status == status_filter)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    scope: TenantScope = Depends(get_tenant_scope),
) -> Order:
    query = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id)
    )
    query = scope.apply_filter(query, Order)

    result = await db.execute(query)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado.")

    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: uuid.UUID,
    body: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    scope: TenantScope = Depends(get_tenant_scope),
) -> Order:
    """
    Atualiza status do pedido e dispara notificação WhatsApp pro cliente.
    Cada transição de status envia uma mensagem diferente.
    """
    query = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.customer))
        .where(Order.id == order_id)
    )
    query = scope.apply_filter(query, Order)

    result = await db.execute(query)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado.")

    old_status = order.status
    order.status = body.status
    await db.commit()

    # Dispara notificação WhatsApp para o cliente se status mudou
    if old_status != body.status and order.customer:
        try:
            await send_status_notification(
                order=order,
                customer_phone=order.customer.phone,
                old_status=old_status,
                new_status=body.status,
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Falhou ao enviar notificação de status para pedido %s", order_id
            )

    # Recarrega com eager load
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id)
    )
    return result.scalar_one()
