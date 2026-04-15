"""Rota de dashboard — métricas e stats."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_admin
from app.database.session import get_db
from app.models.admin_user import AdminUser
from app.models.customer import Customer
from app.models.order import Order, OrderStatus

router = APIRouter()


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> dict:
    """Retorna métricas para o dashboard."""
    today = date.today()
    week_ago = today - timedelta(days=7)

    # Total de pedidos hoje
    orders_today = await db.execute(
        select(func.count(Order.id)).where(
            func.date(Order.created_at) == today,
            Order.status != OrderStatus.CANCELLED,
        )
    )

    # Receita hoje
    revenue_today = await db.execute(
        select(func.sum(Order.total_amount)).where(
            func.date(Order.created_at) == today,
            Order.status == OrderStatus.DELIVERED,
        )
    )

    # Total de clientes
    total_customers = await db.execute(select(func.count(Customer.id)))

    # Pedidos pendentes
    pending_orders = await db.execute(
        select(func.count(Order.id)).where(
            Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PREPARING])
        )
    )

    # Receita da semana
    revenue_week = await db.execute(
        select(func.sum(Order.total_amount)).where(
            func.date(Order.created_at) >= week_ago,
            Order.status == OrderStatus.DELIVERED,
        )
    )

    return {
        "orders_today": orders_today.scalar() or 0,
        "revenue_today": float(revenue_today.scalar() or 0),
        "total_customers": total_customers.scalar() or 0,
        "pending_orders": pending_orders.scalar() or 0,
        "revenue_week": float(revenue_week.scalar() or 0),
    }
